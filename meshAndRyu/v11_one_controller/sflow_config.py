from mininet.log import info
from mininet.util import quietRun
from os import environ, listdir
import re
from json import dumps
from requests import put



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

