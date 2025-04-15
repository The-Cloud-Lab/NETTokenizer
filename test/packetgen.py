from scapy.all import Ether, IP, UDP, Raw, wrpcap

src_mac = "08:c0:eb:a6:de:3c"
dst_mac = "08:c0:eb:99:9c:70"

packets = []
letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

for i in range(1000000):
    eth_layer = Ether(dst=dst_mac, src=src_mac)
    ip_layer = IP(src="172.16.3.99", dst="172.16.3.219")
    udp_layer = UDP(sport=12345, dport=8000)
    payload = letters[i % len(letters)]
    packet = eth_layer / ip_layer / udp_layer / Raw(load=payload)
    packets.append(packet)

wrpcap("multiCharacterUDP.pcap", packets)