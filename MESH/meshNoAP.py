#!/usr/bin/python

# autor: Ramon dos Reis Fontes
# book: Wireless Network Emulation with Mininet-WiFi
# github: https://github.com/ramonfontes/mn-wifi-book-en

import sys

from mininet.log import setLogLevel, info
from mn_wifi.link import wmediumd, mesh
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.wmediumdConnector import interference
from mininet.node import RemoteController



def topology():
    "Create a network."
    # net = Mininet_wifi(link=wmediumd, wmediumd_mode=interference)
    net = Mininet_wifi(link=wmediumd, wmediumd_mode=interference,controller=RemoteController)


    info("*** Creating nodes\n")
    
    
    sta1 = net.addStation('sta1',mac='00:00:00:00:00:01', ip='10.0.0.1/8',position='10,10,0')
    sta2 = net.addStation('sta2',mac='00:00:00:00:00:02', ip='10.0.0.2/8',position='50,20,0')
    sta3 = net.addStation('sta3',mac='00:00:00:00:00:03', ip='10.0.0.3/8',position='100,30,0')
    sta4 = net.addStation('sta4',mac='00:00:00:00:00:04', ip='10.0.0.4/8',position='140,40,0')

    c1=net.addController('c1', controller=RemoteController, ip='127.0.0.1', port=6653)

    info("*** Configuring Propagation Model\n")
    net.setPropagationModel(model="logDistance", exp=4)
    # c1 = net.addController('c1')



    info("*** Configuring wifi nodes\n")
    net.configureWifiNodes()

    info("*** Creating links\n")
    net.addLink(sta1, cls=mesh, ssid='meshNet',
                intf='sta1-wlan0', channel=5)  #, passwd='thisisreallysecret')
    net.addLink(sta2, cls=mesh, ssid='meshNet',
                intf='sta2-wlan0', channel=5)  #, passwd='thisisreallysecret')
    net.addLink(sta3, cls=mesh, ssid='meshNet',
                intf='sta3-wlan0', channel=5)  #, passwd='thisisreallysecret')
    net.addLink(sta4, cls=mesh, ssid='meshNet',
                intf='sta4-wlan0', channel=5)  #, passwd='thisisreallysecret')

    

    net.plotGraph(max_x=200, max_y=200) 

    info("*** Starting network\n")
    net.build()
    c1.start()

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    topology()
