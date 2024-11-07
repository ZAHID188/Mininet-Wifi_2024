# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib import hub
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.app.wsgi import WSGIApplication, ControllerBase, WebSocketRPCServer, websocket,rpc_public
from collections import defaultdict
import time
import json




simple_switch_instance_name = 'simple_switch_api_app'
url = '/simpleswitch/ws'

class MeshTopologyController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'wsgi': WSGIApplication,
    }

    def __init__(self, *args, **kwargs):
        super(MeshTopologyController, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        wsgi.register(
            SimpleSwitchWebSocketController,
            data={simple_switch_instance_name: self},
        )
        self._ws_manager = wsgi.websocketmanager
        self.qos_metrics = QoSMetrics()
        self.mac_to_port = {}
        self.datapaths = {}  #to store datapaths
        # Start monitoring thread
        self.monitor_thread = hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, CONFIG_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == CONFIG_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]

    def _monitor(self):
        while True:
            self._collect_stats()
            hub.sleep(1)  # Collect stats every second

    def _collect_stats(self):
        for dp in self.datapaths.values():
            self._request_stats(dp)

    def _request_stats(self, datapath):
        parser = datapath.ofproto_parser
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)
        
        req = parser.OFPPortStatsRequest(datapath, 0, datapath.ofproto.OFPP_ANY)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        # self._ws_manager.broadcast(str(pkt))  #ws sending packet information
        



        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src

        dpid = format(datapath.id, "d").zfill(16)
        # Send QoS metrics
        metrics = self.qos_metrics.get_metrics(dpid)
        metrics['dpid'] = dpid
        self._ws_manager.broadcast(json.dumps({
            'type': 'qos_metrics',
            'data': metrics
        }))
        self.mac_to_port.setdefault(dpid, {})

        # self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)
        # self._ws_manager.broadcast(" I am zahid")  #ws sending packet check


        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        strDPid=str(dpid)
        
        for stat in body:
            packet_count = stat.packet_count
            byte_count = stat.byte_count
            duration = time.time() - stat.duration_sec
            
            # Calculate metrics
            latency = duration / packet_count if packet_count > 0 else 0
            self.qos_metrics.update_metrics(dpid, byte_count, packet_count, latency)
            
            # Broadcast metrics to WebSocket clients
            metrics = self.qos_metrics.get_metrics(dpid)
            metrics['dpid'] = strDPid
            self._ws_manager.broadcast(json.dumps({
                'type': 'flow_stats',
                'data': metrics
            }))
#port status off
    # @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    # def _port_stats_reply_handler(self, ev):
    #     body = ev.msg.body
    #     dpid = ev.msg.datapath.id
    #     strdpid=str(dpid)
    #     for stat in body:
    #         port_no = stat.port_no
    #         rx_packets = stat.rx_packets
    #         tx_packets = stat.tx_packets
    #         rx_bytes = stat.rx_bytes
    #         tx_bytes = stat.tx_bytes
            
    #         # Send port statistics via WebSocket
    #         port_stats = {
    #             'dpid': strdpid,
    #             'port_no': port_no,
    #             'rx_packets': rx_packets,
    #             'tx_packets': tx_packets,
    #             'rx_bytes': rx_bytes,
    #             'tx_bytes': tx_bytes
    #         }
    #         self._ws_manager.broadcast(json.dumps({
    #             'type': 'port_stats',
    #             'data': port_stats
    #         }))

class SimpleSwitchWebSocketController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(SimpleSwitchWebSocketController, self).__init__(
            req, link, data, **config)
        self.simple_switch_app = data[simple_switch_instance_name]

    @websocket('simpleswitch', url)
    def _websocket_handler(self, ws):
        simple_switch = self.simple_switch_app
        simple_switch.logger.debug('WebSocket connected: %s', ws)
        rpc_server = WebSocketRPCServer(ws, simple_switch)
        rpc_server.serve_forever()
        simple_switch.logger.debug('WebSocket disconnected: %s', ws)

class QoSMetrics:
    def __init__(self):
        self.packet_counts = defaultdict(int)
        self.byte_counts = defaultdict(int)
        self.start_times = defaultdict(float)
        self.latencies = defaultdict(list)
        self.packet_losses = defaultdict(int)
        
    def update_metrics(self, dpid, bytes_count, packet_count, latency):
        self.byte_counts[dpid] += bytes_count
        self.packet_counts[dpid] += packet_count
        self.latencies[dpid].append(latency)
        
    def get_metrics(self, dpid):
        duration = time.time() - self.start_times.get(dpid, time.time())
        if duration == 0:
            throughput = 0
        else:
            throughput = (self.byte_counts[dpid] * 8) / duration  # bits per second
            
        latency = sum(self.latencies[dpid]) / len(self.latencies[dpid]) if self.latencies[dpid] else 0
        
        total_packets = self.packet_counts[dpid] + self.packet_losses[dpid]
        pdr = self.packet_counts[dpid] / total_packets if total_packets > 0 else 1
        
        return {
            'throughput': throughput,
            'latency': latency,
            'pdr': pdr,
            'packet_count': self.packet_counts[dpid],
            'byte_count': self.byte_counts[dpid]
        }