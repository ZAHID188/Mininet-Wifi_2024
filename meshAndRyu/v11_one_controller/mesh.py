#!/usr/bin/env python

"""
This example shows on how to create wireless link between two APs with mesh
The wireless mesh network is based on IEEE 802.11s
"""

from mininet.log import setLogLevel, info
from mn_wifi.link import wmediumd, mesh
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.wmediumdConnector import interference
from mininet.node import RemoteController
from sflow_config import configure_sflow
from Cust_CLI import CustomCLI

# from link import mesh


def topology():
    "Create a network."
    net = Mininet_wifi(controller=RemoteController, link=wmediumd, wmediumd_mode=interference)

    num_stas = 6
    num_aps = 6
    ip_range = "192.168.1"
    max_aps_connect_sta = 1

    info("*** Creating nodes\n")
    stas = []
    for i in range(1, num_stas + 1):
        ip = "{}.{}".format(ip_range, i)
        sta = net.addStation('sta{}'.format(i), mac='00:00:00:00:00:{:02x}'.format(i), ip='{}/24'.format(ip), position='{},{},0'.format(20 + i*10, 51))
        stas.append(sta)
    
    aps = []
    for i in range(1, num_aps + 1):
        ap = net.addAccessPoint('ap{}'.format(i), wlans=2, ssid='ssid{}'.format(i), position='{},{},0'.format(30 + i*20, 60))
        aps.append(ap)

    c1 = net.addController('c1', controller=RemoteController, ip='127.0.0.1', port=6653)

    info("*** Configuring nodes\n")
    net.configureNodes()

    info("*** Associating Stations\n")
    sta_index = 0
    for ap in aps:
        for _ in range(max_aps_connect_sta):
            if sta_index < num_stas:
                net.addLink(stas[sta_index], ap)
                sta_index += 1
    for ap in aps:
        net.addLink(ap, intf='{}-wlan2'.format(ap.name), cls=mesh, ssid='mesh-ssid', channel=5)

    # net.plotGraph(max_x=160, max_y=160) 

    info("*** Starting network\n")
    net.build()
    c1.start()
    for ap in aps:
        ap.start([c1])

    # Configure sFlow -- uncomment this code if sflow server is on
    # configure_sflow(net)

    info("*** Running CLI\n")
    CustomCLI(net)  # Use the custom CLI
    # CLI(net)
    info("*** Stopping network\n")
    net.stop()




if __name__ == '__main__':
    setLogLevel('info')
    topology()