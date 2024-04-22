#!/usr/bin/env python
#IrawanKurnia
#191344014
#4NK
import sys

from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mininet.node import RemoteController

def topology(args):

    # net = Mininet_wifi()
    net = Mininet_wifi(controller=RemoteController)


    info("*** Creating nodes\n")
    h1 = net.addHost( 'h1', mac='00:00:00:00:00:01', ip='10.0.0.1/8' )
    sta1 = net.addStation( 'sta1', mac='00:00:00:00:00:02', ip='10.0.0.2/24', range='20',position='120,120,0')
    sta2 = net.addStation( 'sta2', mac='00:00:00:00:00:03', ip='10.0.0.3/24', range='20',position='20,40,0')
    sta3 = net.addStation( 'sta3', mac='00:00:00:00:00:04', ip='10.0.0.4/24', range='20',position='120,20,0')
    sta4 = net.addStation( 'sta4', mac='00:00:00:00:00:05', ip='10.0.0.5/24', range='20',position='20,120,0')
    ap1 = net.addAccessPoint( 'ap1', ssid= 'ap1-ssid', mode= 'g', channel= '1', position='130,100,0', range='30' )
    ap2 = net.addAccessPoint( 'ap2', ssid= 'ap2-ssid', mode= 'g', channel= '1', position='30,30,0', range='30' )
    ap3 = net.addAccessPoint( 'ap3', ssid= 'ap3-ssid', mode= 'g', channel= '1', position='130,30,0', range='30' )
    ap4 = net.addAccessPoint( 'ap4', ssid= 'ap4-ssid', mode= 'g', channel= '1', position='30,100,0', range='30' )
    ap5 = net.addAccessPoint( 'ap5', ssid= 'ap5-ssid', mode= 'g', channel= '1', position='80,140,0', range='30' )
    # c1 = net.addController( 'c1' )
    c1=net.addController('c1', controller=RemoteController, ip='127.0.0.1', port=6653)

    info("*** Configuring propagation model\n")
    net.setPropagationModel(model="logDistance", exp=4.5)

    info("*** Configuring wifi nodes\n")
    net.configureWifiNodes()

    info("*** Associating and Creating links\n")
    net.addLink(ap1, h1)
    net.addLink(ap1, ap2)
    net.addLink(ap1, ap4)
    net.addLink(ap1, ap3)
    net.addLink(ap2, ap3)
    net.addLink(ap2, ap4)
    net.addLink(ap2, ap5)
    net.addLink(ap3, ap4)
    net.addLink(ap3, ap5)
    net.addLink(ap4, ap5)
    net.addLink(ap5, ap1)
    
    

    if '-p' not in args:
        net.plotGraph(max_x=160, max_y=160)
        
        # net.setMobilityModel(time=0, model="RandomWayPoint", max_x=160, max_y=160, seed=20)


    info("*** Starting network\n")
    net.build()
    c1.start()
    ap1.start([c1])
    ap2.start([c1])
    ap3.start([c1])
    ap4.start([c1])
    ap5.start([c1])

    info("*** Running CLI\n")
    CLI( net )

    info("*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    topology(sys.argv)
