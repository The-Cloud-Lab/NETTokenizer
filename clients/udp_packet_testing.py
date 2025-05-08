import socket
import struct
import asyncio
import time
import random
import string
import matplotlib.pyplot as plt

SRC_MAC = "08:c0:eb:a6:de:3d"
DST_MAC = "08:c0:eb:a6:c6:2d"
IFACE = "enp2s0f1np1"
ETH_TYPE = 0x88B5
SRC_PORT = 12345
DST_PORT = 67

max_batch_size = 100
batch_sizes = list(range(1, max_batch_size + 1))

tokenization_times_us = [] 
token_lengths = []
timestamps = []

def create_ethernet_frame(src_mac, dst_mac, eth_type, payload):
    src_mac_bytes = bytes.fromhex(src_mac.replace(":", ""))
    dst_mac_bytes = bytes.fromhex(dst_mac.replace(":", ""))
    eth_header = dst_mac_bytes + src_mac_bytes + struct.pack("!H", eth_type)
    return eth_header + payload

def create_custom_udp_packet(src_port, dst_port, payload):
    udp_header = struct.pack("!HHHH", src_port, dst_port, 8 + len(payload), 0)
    return udp_header + payload.encode()

def random_word(length):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def handle_packet(packet, tokenization_time_us):
    eth_header_length = 14
    payload = packet[eth_header_length:]
    response_payload = payload.decode('utf-8', errors='ignore').strip('\x00')
    print(f"Tokens received: {response_payload}")
    print(f"Tokenization time: {tokenization_time_us:.2f} µs")

async def send_and_capture(batch_size):
    tokens = [random_word(random.randint(1, 10)) for _ in range(batch_size)]
    payload = " ".join(tokens)
    print(f"Tokens sent: {payload}")
    udp_packet = create_custom_udp_packet(SRC_PORT, DST_PORT, payload)
    eth_frame = create_ethernet_frame(SRC_MAC, DST_MAC, ETH_TYPE, udp_packet)

    sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_TYPE))
    sock.bind((IFACE, 0))

    start_time = time.time()
    sock.send(eth_frame)

    sock.settimeout(15)
    try:
        response = sock.recv(4096)
        end_time = time.time()
        duration_us = (end_time - start_time) * 1_000_000  # microseconds
        tokenization_times_us.append(duration_us)
        timestamps.append(end_time)
        token_lengths.append(len(response))
        handle_packet(response, duration_us)
    except socket.timeout:
        print("No response received within timeout.")
        tokenization_times_us.append(0)
        timestamps.append(time.time())
        token_lengths.append(0)
    finally:
        sock.close()

def plot_graph(batch_sizes, tokenization_times_us):
    batch_sizes = batch_sizes[1:]
    tokenization_times_us = tokenization_times_us[1:]
    plt.figure(figsize=(10, 6))
    plt.plot(batch_sizes, tokenization_times_us, marker='o', color='b')
    plt.title("Tokenization Time vs Tokens per Request")
    plt.xlabel("Tokens per Request")
    plt.ylabel("Tokenization Time (µs)")
    plt.grid(True, which="both", ls="--", linewidth=0.5)
    plt.tight_layout()
    plt.savefig("tokenization_time_graph.png")
    print("Graph saved as tokenization_time_graph.png")

def plot_cdf(tokenization_times_us):
    sorted_times = sorted(tokenization_times_us)
    cumulative = [(i + 1) / len(sorted_times) for i in range(len(sorted_times))]

    plt.figure(figsize=(10, 6))
    plt.plot(sorted_times, cumulative, marker='.', linestyle='-', color='purple')
    plt.title("CDF of Tokenization Time")
    plt.xlabel("Tokenization Time (µs)")
    plt.ylabel("Cumulative Fraction of Requests")
    plt.grid(True, linestyle="--", linewidth=0.5)
    plt.tight_layout()
    plt.savefig("tokenization_time_cdf.png")
    print("CDF Graph saved as tokenization_time_cdf.png")

async def main():
    tasks = [asyncio.create_task(send_and_capture(batch)) for batch in batch_sizes]
    await asyncio.gather(*tasks)
    plot_graph(batch_sizes, tokenization_times_us)
    plot_cdf(tokenization_times_us)

if __name__ == "__main__":
    asyncio.run(main())
