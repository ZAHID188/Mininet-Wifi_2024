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
from ryu import utils
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls,set_ev_handler,CONFIG_DISPATCHER, MAIN_DISPATCHER,HANDSHAKE_DISPATCHER
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
        self.last_stats={}
        #throughput
        self.port_stats = {}
        self.port_speed = {}
        self.flow_stats = {}
        self.flow_speed = {}
        self.sleep_time = 5 
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
            hub.sleep(5)  # Collect stats every second

    def _collect_stats(self):
        for dp in self.datapaths.values():
            self._request_stats(dp)

    def _request_stats(self, datapath):
        parser = datapath.ofproto_parser
        #echo for latency
        echodata = str(time.time()).encode('utf-8')
        echo_req= parser.OFPEchoRequest(datapath,data=echodata)
        datapath.send_msg(echo_req)
        # self.logger.info(f"Sent echo request to switch {datapath.id}")
        #portstatus 

        # Request flow stats
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)
        #Port request
        Portreq = parser.OFPPortStatsRequest(datapath, 0, datapath.ofproto.OFPP_ANY)
        datapath.send_msg(Portreq)

    
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
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
        # metrics = self.qos_metrics.get_metrics(dpid)
        # metrics['dpid'] = dpid
        # self._ws_manager.broadcast(json.dumps({
        #     'type': 'qos_metrics',
        #     'data': metrics
        # }))
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
    
    @set_ev_cls(ofp_event.EventOFPEchoReply, [HANDSHAKE_DISPATCHER, CONFIG_DISPATCHER, MAIN_DISPATCHER])
    def echo_reply_handler(self, ev): 
        now_timestamp = time.time()
        try:
            echo_time = float(ev.msg.data.decode('utf-8'))
            latency = (now_timestamp - echo_time) * 1000  # Convert to milliseconds
            dpid = ev.msg.datapath.id
            strDPid=str(dpid)
            latency= f"{latency:.2f}"
            latency=str(latency)
            # Update latency
            self.qos_metrics.update_metrics(dpid, latency)
        except Exception as e:
            self.logger.error(f'Error processing echo reply: {e}')


    # for throughput
    def _save_stats(self, dist, key, value, length):
        if key not in dist:
            dist[key] = []
        dist[key].append(value)

        if len(dist[key]) > length:
            dist[key].pop(0)

    def _calculate_speed(self, now, pre, period):
        if period:
            return (now - pre) / period
        else:
            return 0

    def _get_speed_in_mbps(self, speed):
        return speed * 8 / 1000000  # Convert to Mbps

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        significant_speed_threshold = 2.0  # Threshold in Mbps to filter out noise
        for stat in sorted(body, key=lambda x: x.port_no):
            port_no = stat.port_no
            if port_no != ev.msg.datapath.ofproto.OFPP_LOCAL:
                key = (dpid, port_no)
                value = (stat.tx_bytes, stat.rx_bytes, stat.tx_errors,
                        stat.rx_errors, stat.duration_sec, stat.duration_nsec)

                self._save_stats(self.port_stats, key, value, 5)

                # Calculate port speed
                pre = 0
                period = self.sleep_time
                tmp = self.port_stats[key]
                if len(tmp) > 1:
                    pre = tmp[-2][0] + tmp[-2][1]  # tx_bytes + rx_bytes
                    
                speed = self._calculate_speed(stat.tx_bytes + stat.rx_bytes,
                                            pre, period)
                
                self._save_stats(self.port_speed, key, speed, 5)
                
                # Calculate throughput in Mbps
                speed_mbps = self._get_speed_in_mbps(speed)

                # Update QoS metrics only if speed exceeds the threshold
                if speed_mbps >= significant_speed_threshold:
                    self.qos_metrics.update_throughput(dpid, port_no, speed_mbps)
                    # self.logger.info("Significant Speed (Mbps): %s", speed_mbps)

                
                
        # self.logger.info(" port %s", dpid )
        # Broadcast metrics
        metrics = self.qos_metrics.get_metrics(dpid)
        metrics['dpid'] = str(dpid)
        self._ws_manager.broadcast(json.dumps({
            'type': 'qos_metrics',
            'data': metrics
        }))



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
        self.latencies = defaultdict(list)
        self.throughputs = defaultdict(dict)  # {dpid: {port_no: throughput}}

    def update_metrics(self, dpid, latency):
        self.latencies[dpid] = latency

    def update_throughput(self, dpid, port_no, throughput):
        # Check if the new throughput value is different from the current one
        if throughput != 0 and self.throughputs[dpid].get(port_no) != throughput:
            self.throughputs[dpid][port_no] = throughput

    def get_metrics(self, dpid):
        total_throughput = sum(self.throughputs[dpid].values()) if dpid in self.throughputs else 0
        return {
            'latency': self.latencies[dpid],
            'throughput': f"{total_throughput:.2f}",
            'port_throughputs': {port: f"{speed:.2f}" for port, speed in self.throughputs[dpid].items()}
        }