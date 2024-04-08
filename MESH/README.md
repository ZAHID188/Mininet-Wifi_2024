# Mininet-Wifi_2024
## Mesh network with sdn controller

- Routing table`sta1 route -n`
- setup a routing protocol or configure routing tables
    - Adding route in table
    - `sta1 ip route add 10.0.0.3 via 10.0.0.2`
    - `sta3 ip route add 10.0.0.1 via 10.0.0.2`
    - `sta2 echo 1 > /proc/sys/net/ipv4/ip_forward`
    - Instructs **sta2** to forward packets addressed to **sta1** and **sta3**
      `mininet-wifi> sta2 echo 1 > /proc/sys/net/ipv4/ip_forward`