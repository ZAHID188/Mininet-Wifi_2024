from ryu.app import simple_switch_13
from ryu.app.wsgi import ControllerBase, rpc_public, websocket, WebSocketRPCServer, WSGIApplication
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls,MAIN_DISPATCHER
from ryu.lib.packet import packet
from ryu.lib import hub
from collections import defaultdict
import time
import json

simple_switch_instance_name = 'simple_switch_api_app'
url = '/simpleswitch/ws'

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

class SimpleSwitchWebSocket13(simple_switch_13.SimpleSwitch13):
    _CONTEXTS = {
        'wsgi': WSGIApplication,
    }

    def __init__(self, *args, **kwargs):
        super(SimpleSwitchWebSocket13, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        wsgi.register(SimpleSwitchWebSocketController, {simple_switch_instance_name: self})
        
        self._ws_manager = wsgi.websocketmanager
        self.qos_metrics = QoSMetrics()
        
        # Start monitoring thread
        self.monitor_thread = hub.spawn(self._monitor)

    def _monitor(self):
        while True:
            self._collect_stats()
            hub.sleep(1)  # Collect stats every second

    def _collect_stats(self):
        for dp in self.datapath.values():
            self._request_stats(dp)

    def _request_stats(self, datapath):
        parser = datapath.ofproto_parser
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)
        
        req = parser.OFPPortStatsRequest(datapath, 0, datapath.ofproto.OFPP_ANY)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        
        for stat in body:
            packet_count = stat.packet_count
            byte_count = stat.byte_count
            duration = time.time() - stat.duration_sec
            
            # Calculate metrics
            latency = duration / packet_count if packet_count > 0 else 0
            self.qos_metrics.update_metrics(dpid, byte_count, packet_count, latency)
            
            # Broadcast metrics to WebSocket clients
            metrics = self.qos_metrics.get_metrics(dpid)
            metrics['dpid'] = dpid
            self._ws_manager.broadcast(json.dumps(metrics))

class SimpleSwitchWebSocketController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(SimpleSwitchWebSocketController, self).__init__(req, link, data, **config)
        self.simple_switch_app = data[simple_switch_instance_name]

    @websocket('simpleswitch', url)
    def _websocket_handler(self, ws):
        simple_switch = self.simple_switch_app
        simple_switch.logger.debug('WebSocket connected: %s', ws)
        rpc_server = WebSocketRPCServer(ws, simple_switch)
        rpc_server.serve_forever()
        simple_switch.logger.debug('WebSocket disconnected: %s', ws)