#!/usr/bin/env python3

from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.node import OVSKernelAP
from ryu.lib.hub import spawn
import ryu.contrib.mac_to_port_behavior
from ryu.ofctl import ofctl_rest

def startRYUController(net):
    # Start the Ryu controller
    info('*** Starting Ryu controller\n')
    ryu_process = spawn(['ryu-manager', '--ofp-tcp-listen-port=6653', 'ryu.app.simple_switch_13'])

    # Set up a one-way gateway to secure the Ryu controller
    info('*** Setting up one-way gateway\n')
    net.get('r1').cmd('iptables -A INPUT -p tcp --dport 6653 -j DROP')
    net.get('r2').cmd('iptables -A INPUT -p tcp --dport 6653 -j DROP')
    net.get('r3').cmd('iptables -A INPUT -p tcp --dport 6653 -j DROP')
    net.get('r4').cmd('iptables -A INPUT -p tcp --dport 6653 -j DROP')
    net.get('r5').cmd('iptables -A INPUT -p tcp --dport 6653 -j DROP')

def topology():
    "Create a mesh network"
    net = Mininet_wifi()

    info("*** Creating nodes\n")
    r1 = net.addAccessPoint('r1', cls=OVSKernelAP, ssid='r1-ssid', mode='g', channel='1')
    r2 = net.addAccessPoint('r2', cls=OVSKernelAP, ssid='r2-ssid', mode='g', channel='6')
    r3 = net.addAccessPoint('r3', cls=OVSKernelAP, ssid='r3-ssid', mode='g', channel='11')
    r4 = net.addAccessPoint('r4', cls=OVSKernelAP, ssid='r4-ssid', mode='g', channel='2')
    r5 = net.addAccessPoint('r5', cls=OVSKernelAP, ssid='r5-ssid', mode='g', channel='7')
    sta1 = net.addStation('sta1', ip='192.168.0.1/24')
    sta2 = net.addStation('sta2', ip='192.168.0.2/24')
    sta3 = net.addStation('sta3', ip='192.168.0.3/24')
    sta4 = net.addStation('sta4', ip='192.168.0.4/24')
    sta5 = net.addStation('sta5', ip='192.168.0.5/24')
    c1 = net.addController('c1')

    info("*** Configuring wifi nodes\n")
    net.configureWifiNodes()

    info("*** Configuring mesh nodes\n")
    r1.setMastermodeRouteGW(intf='r1-wlan0', ssid='r1-ssid', channel='1', mode='n2')
    r2.setMastermodeRouteGW(intf='r2-wlan0', ssid='r2-ssid', channel='6', mode='n2')
    r3.setMastermodeRouteGW(intf='r3-wlan0', ssid='r3-ssid', channel='11', mode='n2')
    r4.setMastermodeRouteGW(intf='r4-wlan0', ssid='r4-ssid', channel='2', mode='n2')
    r5.setMastermodeRouteGW(intf='r5-wlan0', ssid='r5-ssid', channel='7', mode='n2')

    info("*** Creating links\n")
    net.addLink(sta1, r1)
    net.addLink(sta2, r2)
    net.addLink(sta3, r3)
    net.addLink(sta4, r4)
    net.addLink(sta5, r5)
    net.addLink(r1, r2)
    net.addLink(r2, r3)
    net.addLink(r3, r4)
    net.addLink(r4, r5)
    net.addLink(r5, r1)

    info("*** Starting network\n")
    net.build()
    c1.start()
    r1.start([c1])
    r2.start([c1])
    r3.start([c1])
    r4.start([c1])
    r5.start([c1])

    startRYUController(net)

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    topology()