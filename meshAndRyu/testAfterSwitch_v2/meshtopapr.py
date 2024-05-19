#!/usr/bin/python

from mininet.node import Controller,RemoteController , OVSKernelSwitch
from mininet.log import setLogLevel, info
from mn_wifi.net import Mininet_wifi
from mn_wifi.node import Station, OVSKernelAP
from mn_wifi.cli import CLI
from mn_wifi.link import wmediumd
from mn_wifi.wmediumdConnector import interference
from subprocess import call


def myNetwork():

    net = Mininet_wifi(controller=RemoteController, wmediumd_mode=interference, link=wmediumd)

    info( '*** Adding controller\n' )
    c0 = net.addController(name='c0',controller=RemoteController, ip='127.0.0.1',port=6653)

    info( '*** Add switches/APs/sta \n')
    sta1 = net.addStation('sta1', mac='00:00:00:00:00:11', position='470.0,574.0,0')
    sta2 = net.addStation('sta2', mac='00:00:00:00:00:12', position='80.0,382.0,0')
    sta3 = net.addStation('sta3', mac='00:00:00:00:00:13', position='425.0,59.0,0')
    ap1 = net.addAccessPoint('ap1', cls=OVSKernelAP, ssid='ap1-ssid',
                             channel='1', mode='g', position='241.0,478.0,0')
    ap2 = net.addAccessPoint('ap2', cls=OVSKernelAP, ssid='ap2-ssid',
                             channel='1', mode='g', position='529.0,64.0,0')
    
    s1 = net.addSwitch('s1', cls=OVSKernelSwitch)

    info("*** Configuring Propagation Model\n")
    net.setPropagationModel(model="logDistance", exp=3)

    info("*** Configuring wifi nodes\n")
    net.configureWifiNodes()

    info( '*** Add links\n')
    net.addLink(sta1, ap1)
    net.addLink(sta2, ap1)
    net.addLink(sta3, ap2)
    net.addLink(ap1, s1)
    net.addLink(ap2, s1)



   

    net.plotGraph(max_x=1000, max_y=1000)

    info( '*** Starting network\n')
    net.build()
    info( '*** Starting controllers\n')
    for controller in net.controllers:
        controller.start()

    info( '*** Starting switches/APs\n')
    
    net.get('ap1').start([])
    net.get('ap2').start([])
    
    net.get('s1').start([c0])

    info( '*** Post configure nodes\n')

    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel( 'info' )
    myNetwork()

