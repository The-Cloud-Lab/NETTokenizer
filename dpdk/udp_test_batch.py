import socket
import struct
import asyncio
import time
import matplotlib.pyplot as plt

# Configuration
SRC_MAC = "08:c0:eb:a6:de:3d"  # Source MAC address
DST_MAC = "08:c0:eb:a6:c6:2d"   # Destination MAC address (server MAC)
IFACE = "enp2s0f1np1"           # Network interface to send/receive packets
ETH_TYPE = 0x88B5               # Custom EtherType (must match server)
SRC_PORT = 12345                # Source port (client port)
DST_PORT = 67                   # Destination port (server port)

# Load test parameters
max_batch_size = 100  # Maximum batch size to test
batch_sizes = list(range(1, max_batch_size + 1))  # Batch sizes from 1 to max_batch_size

# Lists to store results
tokenization_times = []  # To store tokenization times
token_lengths = []       # To store token lengths

# Function to create an Ethernet frame
def create_ethernet_frame(src_mac, dst_mac, eth_type, payload):
    # Convert MAC addresses to bytes
    src_mac_bytes = bytes.fromhex(src_mac.replace(":", ""))
    dst_mac_bytes = bytes.fromhex(dst_mac.replace(":", ""))
    # Create Ethernet frame
    eth_header = dst_mac_bytes + src_mac_bytes + struct.pack("!H", eth_type)
    return eth_header + payload

# Function to create a custom UDP packet
def create_custom_udp_packet(src_port, dst_port, payload):
    # Create UDP header
    udp_header = struct.pack("!HHHH", src_port, dst_port, 8 + len(payload), 0)
    return udp_header + payload.encode()

# Function to handle incoming packets
def handle_packet(packet, tokenization_time):
    # Extract the payload from the packet (assuming it starts after the Ethernet header)
    eth_header_length = 14  # Ethernet header is 14 bytes
    payload = packet[eth_header_length:]
    # Decode the payload
    response_payload = payload.decode('utf-8', errors='ignore').strip('\x00')
    print(f"Tokens received: {response_payload}")
    print(f"Tokenization time: {tokenization_time:.4f} seconds")  # Print timing with 4 decimal places

# Asynchronous function to send packets and capture responses
async def send_and_capture(batch_size):
    # Create dynamic payload (e.g., "a", "a a", "a a a", ...)
    payload = " ".join(["a"] * batch_size)  # Dynamic payload generation

    # Create the custom UDP packet
    udp_packet = create_custom_udp_packet(SRC_PORT, DST_PORT, payload)

    # Create the Ethernet frame
    eth_frame = create_ethernet_frame(SRC_MAC, DST_MAC, ETH_TYPE, udp_packet)

    print(f"Sending packet with batch size {batch_size} to {DST_MAC} on {IFACE}...")

    # Create a raw socket
    sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_TYPE))
    sock.bind((IFACE, 0))

    # Send the packet
    start_time = time.time()  # Start timing
    sock.send(eth_frame)

    # Wait for a response
    sock.settimeout(5)  # Set a timeout for receiving
    try:
        response = sock.recv(4096)  # Receive up to 4096 bytes
        end_time = time.time()  # End timing
        tokenization_time = end_time - start_time  # Calculate tokenization time
        tokenization_times.append(tokenization_time)  # Store tokenization time
        token_lengths.append(len(response))  # Store token length
        handle_packet(response, tokenization_time)  # Pass tokenization_time to handle_packet
    except socket.timeout:
        print("No response received within timeout.")
    finally:
        sock.close()

# Function to plot and save the graph
def plot_graph(batch_sizes, tokenization_times):
    plt.figure(figsize=(10, 6))

    # Plot tokenization time vs batch size
    plt.plot(batch_sizes, tokenization_times, marker='o', color='b')
    plt.title("Tokenization Time vs Batch Size")
    plt.xlabel("Batch Size")
    plt.ylabel("Tokenization Time (seconds)")
    plt.grid(True)

    # Set y-axis scale to 4 decimal places
    plt.gca().yaxis.set_major_formatter("{x:.4f}")

    # Save the graph locally
    plt.tight_layout()
    plt.savefig("tokenization_time_graph.png")
    print("Graph saved as tokenization_time_graph.png")

# Main function to run the load test
async def main():
    tasks = []
    for batch_size in batch_sizes:
        # Create a task for each batch size
        task = asyncio.create_task(send_and_capture(batch_size))
        tasks.append(task)

    # Wait for all tasks to complete
    await asyncio.gather(*tasks)

    # Plot the graph after all tasks are done
    plot_graph(batch_sizes, tokenization_times)

# Run the script
if __name__ == "__main__":
    asyncio.run(main())
