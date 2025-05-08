#!/usr/bin/env python3
import socket
import struct
import time
import random
import string
import argparse
import csv
import os

IFACE          = "enp2s0f1np1"
ETH_TYPE       = 0x88B5
SRC_PORT       = 12345
DST_PORT       = 67
SRC_MAC        = "08:c0:eb:a6:de:3d"
DST_MAC        = "08:c0:eb:a6:c6:2d"
MAX_PACKET_SIZE= 8192
CSV_FILE       = "throughput_results.csv"

def mac_to_bytes(mac:str) -> bytes:
    return bytes.fromhex(mac.replace(":", ""))

def build_eth_frame(src_mac, dst_mac, eth_type, payload_bytes):
    return dst_mac + src_mac + struct.pack("!H", eth_type) + payload_bytes

def build_udp_packet(src_port, dst_port, payload_bytes):
    length = 8 + len(payload_bytes)
    return struct.pack("!HHHH", src_port, dst_port, length, 0) + payload_bytes

def random_tokens(batch_size:int):
    return " ".join(
        ''.join(random.choices(string.ascii_lowercase, k=random.randint(1,5)))
        for _ in range(batch_size)
    ).encode()

def append_csv_row(row):
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode='a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def main():
    p = argparse.ArgumentParser(
        description="Measure RPS & TPS against your tokenizer server"
    )
    p.add_argument(
        "-e", "--engine",
        choices=["CPU","DPDK"],
        required=True,
        help="Which backend engine to test"
    )
    p.add_argument(
        "-t", "--tokenizer",
        type=str,
        required=True,
        help="Tokenizer name (e.g. gpt2, llama3)"
    )
    p.add_argument(
        "-d", "--duration",
        type=float,
        default=10.0,
        help="Test duration in seconds (default: 10s)"
    )
    p.add_argument(
        "-b", "--batch",
        type=int,
        default=25,
        help="Tokens per request (default: 25)"
    )
    args = p.parse_args()

    src_mac = mac_to_bytes(SRC_MAC)
    dst_mac = mac_to_bytes(DST_MAC)
    sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_TYPE))
    sock.bind((IFACE, 0))
    sock.settimeout(1.0)

    tokens_sent    = 0
    requests_sent  = 0
    requests_succ  = 0

    t0    = time.perf_counter()
    t_end = t0 + args.duration

    print(f"→ Testing engine={args.engine}, tokenizer={args.tokenizer}, "
          f"duration={args.duration}s, batch={args.batch}…")

    while time.perf_counter() < t_end:
        payload = random_tokens(args.batch)
        udp     = build_udp_packet(SRC_PORT, DST_PORT, payload)
        frame   = build_eth_frame(src_mac, dst_mac, ETH_TYPE, udp)

        try:
            sock.send(frame)
            requests_sent += 1
            tokens_sent   += args.batch

            _ = sock.recv(MAX_PACKET_SIZE)
            requests_succ += 1
        except socket.timeout:
            continue

    elapsed = time.perf_counter() - t0
    sock.close()

    rps = requests_succ / elapsed
    tps = tokens_sent    / elapsed

    print("\n──── Results ────")
    print(f"Elapsed time : {elapsed:.2f} s")
    print(f"Requests sent: {requests_sent}, succeeded: {requests_succ}")
    print(f"→ RPS: {rps:,.2f} req/sec")
    print(f"→ TPS: {tps:,.2f} tok/sec")

    append_csv_row({
        "engine":        args.engine,
        "tokenizer":     args.tokenizer,
        "duration_s":    f"{args.duration:.1f}",
        "batch_size":    args.batch,
        "requests_sent": requests_sent,
        "succeeded":     requests_succ,
        "tokens_sent":   tokens_sent,
        "elapsed_s":     f"{elapsed:.3f}",
        "rps":           f"{rps:.2f}",
        "tps":           f"{tps:.2f}",
    })

if __name__ == "__main__":
    main()
