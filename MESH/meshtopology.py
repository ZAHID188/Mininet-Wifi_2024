import sys
from mininet.log import setLogLevel, info
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi

def topology(args):
    net = Mininet_wifi()

    info("*** Creating nodes\n")
    sta1 = net.addStation('sta1', mac='00:00:00:00:00:01', ip='10.0.0.1/8', position='10,10,0')
    sta2 = net.addStation('sta2', mac='00:00:00:00:00:02', ip='10.0.0.2/8', position='90,10,0')
    sta3 = net.addStation('sta3', mac='00:00:00:00:00:03', ip='10.0.0.3/8', position='10,90,0')
    sta4 = net.addStation('sta4', mac='00:00:00:00:00:04', ip='10.0.0.4/8', position='90,90,0')
    ap1 = net.addAccessPoint('ap1', ssid='ap1-ssid', mode='g', channel='1', position='25,30,0')
    ap2 = net.addAccessPoint('ap2', ssid='ap2-ssid', mode='g', channel='1', position='100,30,0')
    ap3 = net.addAccessPoint('ap3', ssid='ap3-ssid', mode='g', channel='1', position='25,110,0')
    ap4 = net.addAccessPoint('ap4', ssid='ap4-ssid', mode='g', channel='1', position='100,110,0')
    ap5 = net.addAccessPoint('ap5', ssid='ap5-ssid', mode='g', channel='1', position='60,130,0')
    c1 = net.addController('c1')

    info("*** Configuring propagation model\n")
    net.setPropagationModel(model="logDistance", exp=4.5)

    info("*** Configuring wifi nodes\n")
    net.configureWifiNodes()

    info("*** Associating Stations with Access Points\n")
    net.addLink(sta1, ap1)
    net.addLink(sta2, ap2)
    net.addLink(sta3, ap3)
    net.addLink(sta4, ap4)

    info("*** Creating mesh links between Access Points\n")
    net.addLink(ap1, ap2)
    net.addLink(ap1, ap3)
    net.addLink(ap1, ap4)
    net.addLink(ap1, ap5)
    net.addLink(ap2, ap3)
    net.addLink(ap2, ap4)
    net.addLink(ap2, ap5)
    net.addLink(ap3, ap4)
    net.addLink(ap3, ap5)
    net.addLink(ap4, ap5)

    if '-p' not in args:
        net.plotGraph(max_x=150, max_y=150)

    info("*** Starting network\n")
    net.build()
    c1.start()
    ap1.start([c1])
    ap2.start([c1])
    ap3.start([c1])
    ap4.start([c1])
    ap5.start([c1])

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    topology(sys.argv[1:])