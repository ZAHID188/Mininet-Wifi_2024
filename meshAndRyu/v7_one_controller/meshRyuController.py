from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ipv4



class MeshWithOWEG(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MeshWithOWEG, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        ip_range = '192.168.1.1'
        num_stas = 6
        self.allowed_ips = self.generate_ip_range(ip_range, num_stas) # Allowed IP addresses
        print(self.allowed_ips)
    
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

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

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
            # ignore lldp packet
            return
        
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if ip_pkt and ip_pkt.src not in self.allowed_ips:
            self.logger.info("Packet from disallowed IP %s dropped", ip_pkt.src)
            return

        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)   ----------------

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # Send packet information to the controller through the one-way gateway
        self.OWEG_topology_to_controller(dpid, src, dst, in_port, ip_pkt.src if ip_pkt else None)

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
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

    def OWEG_topology_to_controller(self, dpid, src, dst, in_port, src_ip):
        """
        Send packet information to the controller through the one-way gateway (OWEG1)
        """
        if src_ip and src_ip in self.allowed_ips:
            self.logger.info("Sending to OWEG1: dpid=%s, src=%s, dst=%s, in_port=%s, src_ip=%s", dpid, src, dst, in_port, src_ip)
            # This is where you would send the data to the controller via OWEG
            pass
        else:
            self.logger.info("Packet from disallowed IP %s dropped", src_ip)

    def OWEG_controller_to_topology(self, parser):
     
        self.logger.info("Receiving from OWEG2")
      
        return [
            {
                'match': parser.OFPMatch(in_port=1, eth_dst='ff:ff:ff:ff:ff:ff'),
                'actions': [parser.OFPActionOutput(2)]
            }
        ]
