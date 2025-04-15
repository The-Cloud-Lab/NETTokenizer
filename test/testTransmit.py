from scapy.all import *

reader = PcapReader("/home/admin1/tokenfettiTest/llm_tokenizer_simulation.pcap")
pkt = next(reader)

print("Before wrapping:")
pkt.show()


eth_pkt = (
    Ether(src="08:c0:eb:a6:de:3d", dst="00:15:4d:13:79:ac", type=0x4d4f) /
    IP(src="172.16.3.99", dst="172.16.3.219") /  
    UDP(sport=12345, dport=8000) /  
    pkt
)

print("After wrapping:")
eth_pkt.show()

sniffer = AsyncSniffer(
    iface="enp2s0f1np1",
    count=1,
    filter=(
        "ether src 08:c0:eb:a6:de:3d && ether dst 00:15:4d:13:79:ac && "
        "ether proto 0x4d4f && ip dst 172.16.3.213 && tcp port 8000"
    )
)
sniffer.start()


sendp(eth_pkt, iface="enp2s0f1np1", count=1)

sniffer.join()

print("\n\nCaptured Packet on Server 1:")
if sniffer.results:
    print(sniffer.results[0].summary())
    sniffer.results[0].show()
else:
    print("No response captured.")
