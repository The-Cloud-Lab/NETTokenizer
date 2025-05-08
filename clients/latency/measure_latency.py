import socket
import struct
import asyncio
import time
import random
import string
import numpy as np
import csv
import os
import matplotlib.pyplot as plt

SRC_MAC = "08:c0:eb:a6:de:3d"
DST_MAC = "08:c0:eb:a6:c6:2d"
IFACE = "enp2s0f1np1"
ETH_TYPE = 0x88B5
SRC_PORT = 12345
DST_PORT = 67

max_batch_size = 75
total_packets = 1000
vocab = "LLaMA3"  # or "LLaMA3"
engine = "CPU"  # or "CPU"

all_tokenization_times = []

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
    print(f"\nTokens sent ({batch_size}): {payload}")
    udp_packet = create_custom_udp_packet(SRC_PORT, DST_PORT, payload)
    eth_frame = create_ethernet_frame(SRC_MAC, DST_MAC, ETH_TYPE, udp_packet)

    print(f"Sending packet with {batch_size} tokens to {DST_MAC} on {IFACE}...")

    sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_TYPE))
    sock.bind((IFACE, 0))

    start_time = time.time()
    sock.send(eth_frame)

    sock.settimeout(5)
    try:
        response = sock.recv(4096)
        end_time = time.time()
        duration_us = (end_time - start_time) * 1_000_000
        all_tokenization_times.append(duration_us)
        handle_packet(response, duration_us)
    except socket.timeout:
        print("No response received within timeout.")
        all_tokenization_times.append(0)
    finally:
        sock.close()

def plot_cdf(times_us, filename):
    times_us = np.array(times_us)
    times_us = times_us[times_us > 0] 

    sorted_times = np.sort(times_us)
    cumulative = np.arange(1, len(sorted_times) + 1) / len(sorted_times)

    p90 = np.percentile(sorted_times, 90)
    p99 = np.percentile(sorted_times, 99)

    plt.figure(figsize=(10, 6))
    plt.plot(sorted_times, cumulative, marker='.', linestyle='-', color='purple', label="CDF")
    plt.axvline(p90, linestyle='--', color='gray', linewidth=0.7)
    plt.axvline(p99, linestyle='--', color='gray', linewidth=0.7)
    plt.axhline(0.9, linestyle='--', color='red', linewidth=0.5, label='90% Threshold')
    plt.axhline(0.99, linestyle='--', color='blue', linewidth=0.5, label='99% Threshold')
    plt.text(p90, 0.05, f'P90: {p90:.1f}µs', rotation=90, fontsize=8)
    plt.text(p99, 0.05, f'P99: {p99:.1f}µs', rotation=90, fontsize=8)

    plt.title(f"CDF of Tokenization Time ({engine}-{vocab}, Batch={max_batch_size})")
    plt.xlabel("Tokenization Time (µs)")
    plt.ylabel("Cumulative Fraction of Requests")
    plt.grid(True, linestyle="--", linewidth=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig(filename)
    print(f"📈 Saved plot to {filename}")

def compute_and_save_stats():
    times = np.array(all_tokenization_times[1:])
    times = times[times > 0]  # Remove timeouts

    if len(times) == 0:
        print("No valid data collected.")
        return

    min_val = np.min(times)
    avg_val = np.mean(times)
    max_val = np.max(times)
    p90_val = np.percentile(times, 90)
    p99_val = np.percentile(times, 99)

    print("\nAggregate stats for entire run (in µs):")
    print(f"{'Min':<10}{'Avg':<10}{'Max':<10}{'P90':<10}{'P99':<10}")
    print(f"{min_val:<10.2f}{avg_val:<10.2f}{max_val:<10.2f}{p90_val:<10.2f}{p99_val:<10.2f}")

    csv_file = "tokenization_summary.csv"
    file_exists = os.path.isfile(csv_file)
    with open(csv_file, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Engine", "Vocab", "Max Batch Size", "Min", "Avg", "Max", "P90", "P99"])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "Engine": engine,
            "Vocab": vocab,
            "Max Batch Size": max_batch_size,
            "Min": min_val,
            "Avg": avg_val,
            "Max": max_val,
            "P90": p90_val,
            "P99": p99_val
        })

    npy_filename = f"{engine}_{vocab}_{max_batch_size}T.npy"
    np.save(npy_filename, times)
    print(f"💾 Saved raw data to {npy_filename}")

    cdf_filename = f"cdf_{engine}_{vocab}_{max_batch_size}T.png"
    plot_cdf(times, cdf_filename)

async def main():
    for _ in range(total_packets):
        batch_size = random.randint(1, max_batch_size)
        await send_and_capture(batch_size)
    compute_and_save_stats()

if __name__ == "__main__":
    asyncio.run(main())
