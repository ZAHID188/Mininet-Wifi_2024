from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ipv4
import time
import threading
import ipaddress




class MeshWithOWEG(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MeshWithOWEG, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        ip_range = '192.168.1.1'
        num_stas = 4
        self.allowed_ips = self.generate_ip_range(ip_range, num_stas) # Allowed IP addresses
        print('Allowed IP by OWEG gateway: ' + ', '.join(self.allowed_ips))
        #network state
        self.network_state = {}
        self.network_traffic = {}
        self.update_network_state_task = threading.Thread(target=self.update_network_state)
        self.update_network_state_task.start()
    
    def generate_ip_range(self,start_ip, count):
        base_ip = start_ip.split('.')
        base_ip = [int(octet) for octet in base_ip]
        ip_set = set()

        for i in range(count):
            ip = '.'.join(map(str, base_ip))
            ip_set.add(ip)
            base_ip[3] += 1  # Increment the last octet
            if base_ip[3] > 255:  # Handle overflow to the next octet
                base_ip[3] = 0
                base_ip[2] += 1

        return ip_set
   
    def update_network_state(self):
         while True:
            print("Network_state- Mesh Accesspoints")
            print(self.network_state)
            print(self.network_traffic)
            time.sleep(10)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        
        
        
        #network state
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def AP_and_ports_state(self, ev):
        datapath = ev.msg.datapath

        #topology state
        if 'switches' not in self.network_state:
            self.network_state['switches'] = {}
        switch_info = {
            'datapath_id': datapath.id,
            'ports': {}
        }
        for port in  datapath.ports.values():
            switch_info['ports'][port.port_no] = {
                'port_no': port.port_no,
                'hw_addr': port.hw_addr,
                'name': port.name,
                'config': port.config,
                'state': port.state,
                'curr': port.curr,
                'advertised': port.advertised,
                'supported': port.supported,
                'peer': port.peer
            }
        self.network_state['switches'][datapath.id] = switch_info

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
            self.logger.debug("hey mesh topo- packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet --- ignore link layer discovery protocol
            return
        
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        OWEG=self.OWEG_topology_to_controller(ip_pkt)
        if OWEG==1:
            return
        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})


        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)  

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]
        self.collect_traffic_info(eth,ip_pkt,in_port,out_port,msg,datapath)

        # Send packet information to the controller through the one-way gateway
        # self.OWEG_topology_to_controller(dpid, src, dst, in_port, ip_pkt.src if ip_pkt else None)

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            # self.OWEG_controller_to_topology(dst)
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
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

        # Receive flow installation instructions from the controller through the one-way gateway
        flow_mod_instructions = self.OWEG_controller_to_topology(parser)

        # Apply the received flow modification instructions
        for instruction in flow_mod_instructions:
            self.add_flow(datapath, 1, instruction['match'], instruction['actions'])
        


    def collect_traffic_info(self,ethernet_pkt,packet_ip,in_port,out_port,massege,datapath):


        #topology state
        if 'traffic' not in self.network_state:
            self.network_traffic['traffic'] = {}
        traffic_info = {}
      
       
     
        if packet_ip!=None:
            traffic_info['packet_in'] = {
                'eth_src': ethernet_pkt.src,
                'eth_dst': ethernet_pkt.dst,
                'ip_src': packet_ip.src,
                'ip_dst': packet_ip.dst,
                # 'tcp_src_port': packet_in.tcp_src_port,
                # 'tcp_dst_port': packet_in.tcp_dst_port
            }

      
        traffic_info['in_port'] = in_port
        traffic_info['out_port'] = out_port

        # Get the packet length and byte count
        packet_len = len(massege.data)
        # byte_count = datapath.get_packet_byte_count(in_port)
        byte_count = "123"

        traffic_info['packet_len'] = packet_len
        traffic_info['byte_count'] = byte_count
        self.network_state['traffic'] = traffic_info

    
      
    def OWEG_topology_to_controller(self, Incoming_IP_packet):
        """
        Send packet information to the controller through the one-way gateway (OWEG1)
        """
    
        if Incoming_IP_packet and Incoming_IP_packet.src and Incoming_IP_packet.src not in self.allowed_ips:
            self.logger.info("Packet from disallowed IP %s dropped", Incoming_IP_packet.src)
            return 1
        else :
            print("ok")


    def OWEG_controller_to_topology(self, parser,outgoing_IP_packet):
        if outgoing_IP_packet and outgoing_IP_packet.dst and outgoing_IP_packet.dst not in self.allowed_ips:
            self.logger.info("DST Packet from disallowed IP %s dropped", outgoing_IP_packet.dst)
            return 1
        else :
            print("dst ok")
     
        self.logger.info(parser)
      
        return [
            {
                'match': parser.OFPMatch(in_port=1, eth_dst='ff:ff:ff:ff:ff:ff'),
                'actions': [parser.OFPActionOutput(2)]
            }
        ]
      
        # def OWEG_controller_to_topology(self, parser):
     
    #     self.logger.info(parser)
      
    #     return [
    #         {
    #             'match': parser.OFPMatch(in_port=1, eth_dst='ff:ff:ff:ff:ff:ff'),
    #             'actions': [parser.OFPActionOutput(2)]
    #         }
    #     ]
