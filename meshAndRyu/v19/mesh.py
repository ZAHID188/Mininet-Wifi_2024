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
from mininet.node import RemoteController, OVSKernelSwitch


def topology():
    "Create a network."
    net = Mininet_wifi(controller=RemoteController, link=wmediumd, wmediumd_mode=interference)

    info("*** Creating nodes\n")
    sta1 = net.addStation('sta1', mac='00:00:00:00:00:11', position='20,51,0')
    sta2 = net.addStation('sta2', mac='00:00:00:00:00:12', position='51,51,0')
    sta3 = net.addStation('sta3', mac='00:00:00:00:00:13', position='81,51,0')
    sta4 = net.addStation('sta4', mac='00:00:00:00:00:14', position='105,51,0')
    sta5 = net.addStation('sta5', mac='00:00:00:00:00:15', position='120,51,0')
    sta6 = net.addStation('sta6', mac='00:00:00:00:00:16', position='130,51,0')
    sta7 = net.addStation('sta7', mac='00:00:00:00:00:17', position='140,51,0')
    sta8 = net.addStation('sta8', mac='00:00:00:00:00:18', position='150,51,0')
    sta9 = net.addStation('sta9', mac='00:00:00:00:00:19', position='160,51,0')
    sta10 = net.addStation('sta10', mac='00:00:00:00:00:20', position='170,51,0')
    sta11 = net.addStation('sta11', mac='00:00:00:00:00:21', position='180,51,0')
    sta12 = net.addStation('sta12', mac='00:00:00:00:00:22', position='190,51,0')


    ap1 = net.addAccessPoint('ap1', wlans=2, ssid='ssid1', position='30,60,0')
    ap2 = net.addAccessPoint('ap2', wlans=2, ssid='ssid2', position='50,60,0')
    ap3 = net.addAccessPoint('ap3', wlans=2, ssid='ssid3', position='70,60,0')
    ap4 = net.addAccessPoint('ap4', wlans=2, ssid='ssid4', position='100,60,0')
    # c1 = net.addController('c1', controller=RemoteController, ip='127.0.0.1', port=6653)
    # c1 = net.addController('c1', controller=RemoteController, ip='192.168.1.100', port=6653)
    c1 = net.addController('c1', controller=RemoteController, ip='192.168.56.1', port=6653)




    info("*** Configuring nodes\n")
    net.configureNodes()

    info("*** Associating Stations\n")
    net.addLink(sta1, ap1)
    net.addLink(sta2, ap1)
    net.addLink(sta3, ap1)
    net.addLink(sta4, ap2)
    net.addLink(sta5, ap2)
    net.addLink(sta6, ap2)
    net.addLink(sta7, ap3)
    net.addLink(sta8, ap3)
    net.addLink(sta9, ap3)
    net.addLink(sta10, ap4)
    net.addLink(sta11, ap4)
    net.addLink(sta12, ap4)
    net.addLink(ap1, intf='ap1-wlan2', cls=mesh, ssid='mesh-ssid', channel=5)
    net.addLink(ap2, intf='ap2-wlan2', cls=mesh, ssid='mesh-ssid', channel=5)
    net.addLink(ap3, intf='ap3-wlan2', cls=mesh, ssid='mesh-ssid', channel=5)
    net.addLink(ap4, intf='ap4-wlan2', cls=mesh, ssid='mesh-ssid', channel=5)


    # net.plotGraph(max_x=160, max_y=160) 

    info("***Starting network\n")
    net.build()
    c1.start()
    ap1.start([c1])
    ap2.start([c1])
    ap3.start([c1])
    ap4.start([c1])

    
    info("*** Running CLI\n")
    CLI(net)
    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology()
