import socket
import struct
from transformers import AutoTokenizer, GPT2Tokenizer
import time

IFACE = "enp2s0f1np1"
ETH_TYPE = 0x88B5
UDP_PORT = 67
MAX_PACKET_SIZE = 8192

tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
#tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.2-1B", trust_remote_code=True)

def decode_udp_payload(packet):
    eth_hdr_len = 14
    udp_hdr_offset = eth_hdr_len + 20  # skip IP (not used but pretend it's there)
    udp_payload_offset = eth_hdr_len + 8
    return packet[udp_payload_offset:].rstrip(b'\x00').decode('utf-8', 'ignore')

def build_udp_response(src_mac, dst_mac, src_port, dst_port, payload_str):
    eth_header = dst_mac + src_mac + struct.pack("!H", ETH_TYPE)

    payload_bytes = payload_str.encode()
    udp_length = 8 + len(payload_bytes)
    udp_header = struct.pack("!HHHH", src_port, dst_port, udp_length, 0)

    return eth_header + udp_header + payload_bytes

def main():
    raw_socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_TYPE))
    raw_socket.bind((IFACE, 0))
    print(f"Listening on interface {IFACE} for ETH_TYPE 0x{ETH_TYPE:X}")

    while True:
        packet, addr = raw_socket.recvfrom(MAX_PACKET_SIZE)

        if len(packet) < 42:
            continue 

        eth_hdr = packet[:14]
        dst_mac, src_mac, eth_type = struct.unpack("!6s6sH", eth_hdr)
        if eth_type != ETH_TYPE:
            continue


        udp_hdr = packet[14:22]
        src_port, dst_port, udp_len, udp_cksum = struct.unpack("!HHHH", udp_hdr)
        if dst_port != UDP_PORT:
            continue

        payload = decode_udp_payload(packet)
        if not payload:
            continue

        start = time.perf_counter()
        input_ids = tokenizer.encode(payload, add_special_tokens=True)
        end = time.perf_counter()

        tokenization_time = (end - start) * 1e6
        print(f"Received: {payload}")
        print(f"Tokens: {len(input_ids)} | ⏱ {tokenization_time:.2f} µs")


        response_str = " ".join(map(str, input_ids))
        response_packet = build_udp_response(dst_mac, src_mac, dst_port, src_port, response_str)
        raw_socket.send(response_packet)

if __name__ == "__main__":
    main()
