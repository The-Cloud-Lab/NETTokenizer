# NETTokenizer

## Overview

NETTokenizer is a DPDK-based in-network tokenizer that provides low latency, high throughput packet processing capabilities. It supports both CPU and DPDK-based tokenizers, and includes benchmarking clients for performance testing.

## Repository Structure

```
NETTokenizer/
├── cpuTokenizer/            # CPU-based tokenizer in Python
│   └── tokenizer.py
├── dpdk/                    # Main DPDK tokenizer implementation
│   ├── tokenizer.c
│   ├── data.json
│   └── README.md
├── dpdk_server_iterations/  # Iterative DPDK server versions for benchmarking
│   ├── tokenizer_1.c
│   ├── tokenizer_2.c
│   ├── tokenizer_3.c
│   ├── tokenizer_4.c
│   ├── tokenizer_5.c
│   └── tokenizer_6.c
├── python_tokenizers/       # Python implementations of different tokenizers
│   ├── server_bert.py
│   ├── server_msmacro.py
│   ├── server_paraphrase.py
│   └── multi_server_load_test.py
├── clients/                 # Client-side benchmarking utilities
│   ├── udp_packet_testing.py
│   ├── latency/
│   │   ├── measure_latency.py
│   │   ├── plot_latency.py
│   │   └── plot_latency_quantiles.py
│   └── throughput/
│       ├── measure_throughput.py
│       └── plot_throughput.py
├── test/                    # PCAP files and test scripts
│   ├── 100SmallPacketUDP.pcap
│   ├── 100kSmallPacketUDP.pcap
│   ├── 1MSmallPacketUDP.pcap
│   ├── singleCharacterPacket.pcap
│   ├── singleCharacterUDP.pcap
│   ├── llm_tokenizer_simulation.pcap
│   ├── myudp.pcap
│   └── testTransmit.py
├── vocab/                   # Vocabulary JSON files and generation script
│   ├── gpt2_vocab.json
│   ├── llama3_vocab.json
│   └── createVocab.py
└── README.md
```

## Prerequisites

* Ubuntu 20.04 LTS or later
* GCC compiler
* Make build system
* Python 3.6 or later

## DPDK Installation & Setup

### 1. Install Dependencies

```bash
sudo apt update
sudo apt install -y build-essential python3 python3-pip ninja-build meson pkg-config libnuma-dev
```

### 2. Download & Install DPDK

```bash
wget https://fast.dpdk.org/rel/dpdk-22.11.2.tar.xz
tar xf dpdk-22.11.2.tar.xz
cd dpdk-22.11.2
meson build
cd build
ninja
sudo ninja install
sudo ldconfig
```

### 3. Configure Hugepages

```bash
# Reserve 1024 2MB hugepages
echo 1024 | sudo tee /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages

# Make the configuration persistent
echo "vm.nr_hugepages=1024" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Create mount point and mount hugepages
sudo mkdir -p /mnt/huge
sudo mount -t hugetlbfs nodev /mnt/huge
```

### 4. Configure Network Interface Cards

```bash
# Load required modules
sudo modprobe uio
sudo modprobe uio_pci_generic

# Bind your NIC to DPDK-compatible driver (replace XX:XX.X with your NIC PCI address)
sudo dpdk-devbind.py --bind=uio_pci_generic XX:XX.X
```

## Building NETTokenizer

```bash
cd dpdk
make
```

## Running the Application

```bash
sudo ./build/tokenizer -l 0-3 -n 4 -- [additional parameters]
```

### Command Line Parameters

* `-l`: CPU cores to use
* `-n`: Memory channels
* Additional parameters can be specified after `--`

## License

MIT License

Copyright (c) \[2025] \[The-Cloud-Lab]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Contact

* Sudarshan Mehta - [smehta3@scu.edu](mailto:smehta3@scu.edu)
* Shaunak Galvankar - [sgalvankar@scu.edu](mailto:sgalvankar@scu.edu)
* Sean Choi - [sean.choi@scu.edu](mailto:sean.choi@scu.edu)
