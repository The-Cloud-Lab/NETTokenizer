# UDP Tokenizer Setup Guide

## Prerequisites
- Ensure the client and server are physically connected using a QSFP cable for proper UDP packet dumping.
- Install DPDK on the system and configure the BlueField SmartNIC correctly.

## Compiling and Running `tokenizer.c`

### Compilation
Use the following command to compile `tokenizer.c`:

```sh
gcc -o tokenizer tokenizer.c \
    -I/usr/local/dpdk/include \
    -L/usr/local/dpdk/lib/x86_64-linux-gnu \
    -lrte_eal -lrte_ethdev -lrte_mbuf -lrte_mempool -lrte_hash -lrte_ring -lcjson -mssse3
```

### Execution
Run the compiled binary with:

```sh
sudo ./tokenizer -l 0 n 1
```

### Sample Run Output
```sh
admin3@admin3:~/development/testing4$ sudo ./tokenizer -l 0 n 1
Initializing EAL...
EAL: Detected CPU lcores: 16
EAL: Detected NUMA nodes: 1
EAL: Detected shared linkage of DPDK
EAL: Multi-process socket /var/run/dpdk/rte/mp_socket
EAL: Selected IOVA mode 'VA'
EAL: VFIO support initialized
mlx5_common: No Verbs device matches PCI device 0000:02:00.0, are kernel drivers loaded?
mlx5_common: Verbs device not found: 0000:02:00.0
mlx5_common: Failed to initialize device context.
PCI_BUS: Requested device 0000:02:00.0 cannot be used
EAL initialized successfully
Getting device info for port 0...
Using device: mlx5_pci (PCI address: 0000:02:00.1)
Creating mbuf pool...
MBUF pool created with buffer size 8320 bytes
Found 3 available Ethernet ports
Configuring device port 0...
Device configured successfully
Setting up RX queue...
RX queue setup complete
Setting up TX queue...
TX queue setup complete
Starting device port 0...
Port 0 started successfully
Enabling promiscuous mode on port 0...
Port 0 in promiscuous mode
Loading hash table...
Creating hash table from data.json...
Hash table created successfully
Added 26 entries to hash table
Hash table loaded successfully
Running lcore_main directly in main thread...
Entering lcore_main on core 0
Core 0 is enabled and running
Waiting for packets on port 0 (core 0)...
```

## Verifying BlueField SmartNIC State
Ensure that the BlueField SmartNIC is recognized correctly and has the required configuration:

```sh
Network devices using DPDK-compatible driver
============================================
0000:02:00.0 'MT42822 BlueField-2 integrated ConnectX-6 Dx network controller a2d6' drv=vfio-pci unused=mlx5_core

Network devices using kernel driver
===================================
0000:02:00.1 'MT42822 BlueField-2 integrated ConnectX-6 Dx network controller a2d6' if=enp2s0f1np1 drv=mlx5_core unused=vfio-pci
0000:41:00.0 'MT2892 Family [ConnectX-6 Dx] 101d' if=enp65s0f0np0 drv=mlx5_core unused=vfio-pci
0000:41:00.1 'MT2892 Family [ConnectX-6 Dx] 101d' if=enp65s0f1np1 drv=mlx5_core unused=vfio-pci
0000:c1:00.0 'NetXtreme BCM5720 Gigabit Ethernet PCIe 165f' if=eno1 drv=tg3 unused=vfio-pci *Active*
0000:c1:00.1 'NetXtreme BCM5720 Gigabit Ethernet PCIe 165f' if=eno2 drv=tg3 unused=vfio-pci
```

## Running `udp_test_batch.py`

### Configuration
Before running `udp_test_batch.py`, ensure the following configurations are set correctly:

```python
# Configuration
SRC_MAC = "08:c0:eb:a6:de:3d"  # Source MAC address
DST_MAC = "08:c0:eb:a6:c6:2d"   # Destination MAC address (server MAC)
IFACE = "enp2s0f1np1"           # Network interface to send/receive packets
ETH_TYPE = 0x88B5               # Custom EtherType (must match server)
SRC_PORT = 12345                # Source port (client port)
DST_PORT = 67                   # Destination port (server port)
```

### Execution
Run the script with:

```sh
sudo python3 udp_test_batch.py
```

### Sample Run Output
```sh
admin1@admin1:~/development/scripts$ sudo python3 udp_test_batch.py 
[sudo] password for admin1: 
Sending packet with batch size 1 to 08:c0:eb:a6:c6:2d on enp2s0f1np1...
Tokens received: C09101 1 102 
Tokenization time: 0.0035 seconds
Sending packet with batch size 2 to 08:c0:eb:a6:c6:2d on enp2s0f1np1...
Tokens received: C09101 1 1 102 
Tokenization time: 0.0000 seconds
Sending packet with batch size 3 to 08:c0:eb:a6:c6:2d on enp2s0f1np1...
Tokens received: C09101 1 1 1 102 
Tokenization time: 0.0000 seconds
Sending packet with batch size 4 to 08:c0:eb:a6:c6:2d on enp2s0f1np1...
Tokens received: C09101 1 1 1 1 102 
```

