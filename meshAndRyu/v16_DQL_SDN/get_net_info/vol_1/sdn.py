# ryu_controller.py
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet
from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link
import websocket
import json
import threading
import time

class NetworkMonitor(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(NetworkMonitor, self).__init__(*args, **kwargs)
        self.topology_api_app = self
        self.switches = []
        self.links = []
        self.ws = None
        self.websocket_thread = threading.Thread(target=self.websocket_run)
        self.websocket_thread.daemon = True
        self.websocket_thread.start()

    def websocket_run(self):
        while True:
            try:
                self.ws = websocket.WebSocketApp("ws://127.0.0.1:8000",
                                                 on_open=self.on_ws_open,
                                                 on_message=self.on_ws_message,
                                                 on_error=self.on_ws_error,
                                                 on_close=self.on_ws_close)
                self.ws.run_forever(reconnect=5)  # Attempt to reconnect every 5 seconds
            except Exception as e:
                self.logger.error(f"WebSocket connection failed: {e}")
                time.sleep(5)  # Wait for 5 seconds before trying to reconnect

    def on_ws_open(self, ws):
        self.logger.info("WebSocket connection opened")

    def on_ws_message(self, ws, message):
        self.logger.info(f"Received message: {message}")

    def on_ws_error(self, ws, error):
        self.logger.error(f"WebSocket error: {error}")

    def on_ws_close(self, ws, close_status_code, close_msg):
        self.logger.info(f"WebSocket connection closed: {close_status_code} - {close_msg}")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(event.EventSwitchEnter)
    def get_topology_data(self, ev):
        switch_list = get_switch(self.topology_api_app, None)
        self.switches = [switch.dp.id for switch in switch_list]
        links_list = get_link(self.topology_api_app, None)
        self.links = [(link.src.dpid, link.dst.dpid) for link in links_list]
        self.send_network_info_to_api()

    def send_network_info_to_api(self):
        network_info = {
            "switches": self.switches,
            "links": self.links
        }
        if self.ws and self.ws.sock and self.ws.sock.connected:
            try:
                self.ws.send(json.dumps(network_info))
                self.logger.info("Network information sent to Flask API successfully")
            except Exception as e:
                self.logger.error(f"Error sending network information: {e}")
        else:
            self.logger.error("WebSocket is not connected")