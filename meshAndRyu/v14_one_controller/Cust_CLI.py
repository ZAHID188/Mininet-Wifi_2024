from mininet.cli import CLI
from os import environ, listdir


class CustomCLI(CLI):
    def do_show_ips(self, _line):
        "Show IP addresses of all stations: show_ips"
        for sta in self.mn.stations:
            print("{}: {}".format(sta.name, sta.IP()))