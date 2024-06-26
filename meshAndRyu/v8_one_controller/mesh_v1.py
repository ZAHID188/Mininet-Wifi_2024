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
from mininet.util import quietRun
from os import environ, listdir
import re
from json import dumps
from requests import put





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

    info("***Starting network\n")
    net.build()
    c1.start()
    for ap in aps:
        ap.start([c1])

    # Configure sFlow
    configure_sflow(net)

    info("*** Running CLI\n")
    CLI(net)
    info("*** Stopping network\n")
    net.stop()


def configure_sflow(net):
    info("*** Configuring sFlow\n")
    ifname = 'enp2s0'  # have to be changed to your own iface!
    collector = environ.get('COLLECTOR', '127.0.0.1')
    sampling = environ.get('SAMPLING', '10')
    polling = environ.get('POLLING', '10')
    sflow = 'ovs-vsctl -- --id=@sflow create sflow agent=%s target=%s ' \
            'sampling=%s polling=%s --' % (ifname, collector, sampling, polling)

    for ap in net.aps:
        sflow += ' -- set bridge %s sflow=@sflow' % ap
        info(' '.join([ap.name for ap in net.aps]))
        quietRun(sflow)

    agent = '127.0.0.1'
    topo = {'nodes': {}, 'links': {}}
    for ap in net.aps:
        topo['nodes'][ap.name] = {'agent': agent, 'ports': {}}

    path = '/sys/devices/virtual/mac80211_hwsim/'
    for child in listdir(path):
        dir_ = '/sys/devices/virtual/mac80211_hwsim/' + '%s' % child + '/net/'
        for child_ in listdir(dir_):
            node = child_[:3]
            if node in topo['nodes']:
                ifindex = open(dir_ + child_ + '/ifindex').read().split('\n', 1)[0]
                topo['nodes'][node]['ports'][child_] = {'ifindex': ifindex}

    path = '/sys/devices/virtual/net/'
    for child in listdir(path):
        parts = re.match('(^.+)-(.+)', child)
        if parts is None:
            continue
        if parts.group(1) in topo['nodes']:
            ifindex = open(path + child + '/ifindex').read().split('\n', 1)[0]
            topo['nodes'][parts.group(1)]['ports'][child] = {'ifindex': ifindex}

    linkName = '%s-%s' % (net.aps[0].name, net.aps[1].name)
    topo['links'][linkName] = {'node1': net.aps[0].name, 'port1': 'ap1-mp2',
                               'node2': net.aps[1].name, 'port2': 'ap2-mp2'}
    linkName = '%s-%s' % (net.aps[1].name, net.aps[2].name)
    topo['links'][linkName] = {'node1': net.aps[1].name, 'port1': 'ap2-mp2',
                               'node2': net.aps[2].name, 'port2': 'ap3-mp2'}
    linkName = '%s-%s' % (net.aps[0].name, net.aps[1].name)
    topo['links'][linkName] = {'node1': net.aps[0].name, 'port1': net.aps[0].wintfs[0].name,
                               'node2': net.aps[1].name, 'port2': net.aps[1].wintfs[0].name}

    put('http://127.0.0.1:8008/topology/json', data=dumps(topo))

if __name__ == '__main__':
    setLogLevel('info')
    topology()