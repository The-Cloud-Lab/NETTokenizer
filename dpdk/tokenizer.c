#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_mbuf.h>
#include <rte_hash.h>
#include <rte_jhash.h>
#include <cjson/cJSON.h>

#define RX_RING_SIZE 4096  // Increased RX queue size
#define TX_RING_SIZE 4096  // Increased TX queue size
#define NUM_MBUFS 65535    // Increased number of MBUFs
#define MBUF_CACHE_SIZE 512
#define BURST_SIZE 64
#define HASH_TABLE_SIZE 65536
#define MAX_SEQUENCE_LENGTH 512
#define MAX_PACKET_SIZE 8192
#define MBUF_SIZE (MAX_PACKET_SIZE + RTE_PKTMBUF_HEADROOM)  // 8192 + 128 = 8320

struct rte_hash *hash_table;
struct rte_mempool *mbuf_pool;

int create_hash_table_from_json(const char *json_file) {
    printf("Creating hash table from %s...\n", json_file);
    FILE *file = fopen(json_file, "r");
    if (!file) {
        printf("Error: Could not open JSON file '%s'\n", json_file);
        return -1;
    }
    fseek(file, 0, SEEK_END);
    long file_size = ftell(file);
    fseek(file, 0, SEEK_SET);
    char *json_data = malloc(file_size + 1);
    fread(json_data, 1, file_size, file);
    fclose(file);
    json_data[file_size] = '\0';
    cJSON *json = cJSON_Parse(json_data);
    if (!json) {
        printf("Error: Failed to parse JSON: %s\n", cJSON_GetErrorPtr());
        free(json_data);
        return -1;
    }
    struct rte_hash_parameters hash_params = {
        .name = "json_hash_table",
        .entries = HASH_TABLE_SIZE,
        .key_len = 32,
        .hash_func = rte_jhash,
        .hash_func_init_val = 0,
    };
    hash_table = rte_hash_create(&hash_params);
    if (!hash_table) {
        printf("Error: Failed to create hash table\n");
        cJSON_Delete(json);
        free(json_data);
        return -1;
    }
    printf("Hash table created successfully\n");
    int count = 0;
    cJSON *item;
    cJSON_ArrayForEach(item, json) {
        char *key = item->string;
        int value = item->valueint;
        char padded_key[32] = {0};
        size_t key_len = strlen(key);
        if (key_len > 32) key_len = 32;
        memcpy(padded_key, key, key_len);
        int *value_ptr = malloc(sizeof(int));
        *value_ptr = value;
        int ret = rte_hash_add_key_data(hash_table, padded_key, value_ptr);
        if (ret < 0) {
            free(value_ptr);
            printf("Warning: Failed to add key '%s' to hash table\n", key);
        } else {
            count++;
        }
    }
    printf("Added %d entries to hash table\n", count);
    cJSON_Delete(json);
    free(json_data);
    return 0;
}

void tokenize_text(const char *text, int *input_ids, int *attention_mask) {
    if (!hash_table) {
        printf("Error: hash_table is NULL\n");
        return;
    }
    size_t len = strlen(text);
    printf("Tokenizing text: %s (length: %zu)\n", text, len);
    input_ids[0] = 101;  // [CLS] token
    attention_mask[0] = 1;
    int token_pos = 1;
    for (int i = 0; i < len && token_pos < MAX_SEQUENCE_LENGTH - 1; i++) {
        char key[2] = {text[i], '\0'};
        char padded_key[32] = {0};
        memcpy(padded_key, key, 1);
        int *value = NULL;
        int ret = rte_hash_lookup_data(hash_table, padded_key, (void **)&value);
        if (ret >= 0 && value) {
            input_ids[token_pos] = *value;
            attention_mask[token_pos] = 1;
            token_pos++;
        }
    }
    if (token_pos < MAX_SEQUENCE_LENGTH) {
        input_ids[token_pos] = 102;  // [SEP] token
        attention_mask[token_pos] = 1;
    }
}

static int lcore_main(__rte_unused void *arg) {
    uint16_t port_id = 0;
    struct rte_mbuf *bufs[BURST_SIZE];
    const uint16_t UDP_PORT = 67;
    uint64_t dropped_packets = 0;

    unsigned lcore_id = rte_lcore_id();
    printf("Entering lcore_main on core %u\n", lcore_id);
    fflush(stdout);
    if (!rte_lcore_is_enabled(lcore_id)) {
        printf("Core %u is not enabled!\n", lcore_id);
        fflush(stdout);
        return -1;
    }
    printf("Core %u is enabled and running\n", lcore_id);
    fflush(stdout);
    printf("Waiting for packets on port %u (core %u)...\n", port_id, lcore_id);
    fflush(stdout);

    while (1) {
        uint16_t nb_rx = rte_eth_rx_burst(port_id, 0, bufs, BURST_SIZE);
        if (nb_rx == 0) {
            continue;
        }
        printf("Received %u packets on core %u\n", nb_rx, lcore_id);
        fflush(stdout);

        for (int i = 0; i < nb_rx; i++) {
            struct rte_mbuf *m = bufs[i];
            if (!m || m->pkt_len < sizeof(struct rte_ether_hdr) + sizeof(struct rte_udp_hdr)) {
                printf("Invalid packet size: %u bytes\n", m ? m->pkt_len : 0);
                dropped_packets++;
                rte_pktmbuf_free(m);
                continue;
            }

            struct rte_ether_hdr *eth_hdr = rte_pktmbuf_mtod(m, struct rte_ether_hdr *);
            struct rte_udp_hdr *udp_hdr = (struct rte_udp_hdr *)(eth_hdr + 1);
            if (rte_be_to_cpu_16(udp_hdr->dst_port) != UDP_PORT) {
                printf("Dropping packet with wrong UDP port: %u\n", rte_be_to_cpu_16(udp_hdr->dst_port));
                dropped_packets++;
                rte_pktmbuf_free(m);
                continue;
            }

            char *payload = (char *)(udp_hdr + 1);
            int payload_len = rte_be_to_cpu_16(udp_hdr->dgram_len) - sizeof(struct rte_udp_hdr);
            if (payload_len <= 0 || payload_len > MAX_PACKET_SIZE) {
                printf("Invalid payload length: %d\n", payload_len);
                dropped_packets++;
                rte_pktmbuf_free(m);
                continue;
            }
            payload[payload_len] = '\0';
            printf("Received Data: %.*s\n", payload_len, payload);
            fflush(stdout);

            // Tokenize the input text
            int input_ids[MAX_SEQUENCE_LENGTH] = {0};
            int attention_mask[MAX_SEQUENCE_LENGTH] = {0};
            tokenize_text(payload, input_ids, attention_mask);

            // Prepare the response payload
            char response_payload[MAX_PACKET_SIZE] = {0};
            int offset = 0;
            for (int j = 0; j < MAX_SEQUENCE_LENGTH && input_ids[j] != 0; j++) {
                offset += snprintf(response_payload + offset, MAX_PACKET_SIZE - offset, "%d ", input_ids[j]);
            }
            printf("Tokenized output: %s\n", response_payload);
            fflush(stdout);

            // Allocate a new mbuf for the response
            struct rte_mbuf *response_mbuf = rte_pktmbuf_alloc(mbuf_pool);
            if (!response_mbuf) {
                printf("Failed to allocate response mbuf\n");
                rte_pktmbuf_free(m);
                dropped_packets++;
                continue;
            }

            // Construct the response packet
            char *data_ptr = rte_pktmbuf_append(response_mbuf, sizeof(struct rte_ether_hdr) + sizeof(struct rte_udp_hdr) + strlen(response_payload));
            if (!data_ptr) {
                printf("Failed to append data to response mbuf\n");
                rte_pktmbuf_free(response_mbuf);
                rte_pktmbuf_free(m);
                dropped_packets++;
                continue;
            }

            // Copy Ethernet header (swap source and destination MAC addresses)
            struct rte_ether_hdr *resp_eth_hdr = (struct rte_ether_hdr *)data_ptr;
            rte_ether_addr_copy(&eth_hdr->src_addr, &resp_eth_hdr->dst_addr);
            rte_eth_macaddr_get(port_id, &resp_eth_hdr->src_addr);
            resp_eth_hdr->ether_type = eth_hdr->ether_type;

            // Copy UDP header (swap source and destination ports)
            struct rte_udp_hdr *resp_udp_hdr = (struct rte_udp_hdr *)(resp_eth_hdr + 1);
            resp_udp_hdr->src_port = udp_hdr->dst_port;
            resp_udp_hdr->dst_port = udp_hdr->src_port;
            resp_udp_hdr->dgram_len = rte_cpu_to_be_16(sizeof(struct rte_udp_hdr) + strlen(response_payload));
            resp_udp_hdr->dgram_cksum = 0;  // No checksum calculation for simplicity

            // Copy the response payload
            char *resp_payload = (char *)(resp_udp_hdr + 1);
            memcpy(resp_payload, response_payload, strlen(response_payload));

            // Send the response packet
            uint16_t nb_tx = rte_eth_tx_burst(port_id, 0, &response_mbuf, 1);
            if (nb_tx < 1) {
                printf("Failed to transmit response (dropped packet #%lu)\n", dropped_packets + 1);
                rte_pktmbuf_free(response_mbuf);
                dropped_packets++;
            } else {
                printf("Response transmitted successfully\n");
            }
            fflush(stdout);

            // Free the original packet
            rte_pktmbuf_free(m);
        }

        if (dropped_packets > 0) {
            printf("Total dropped packets so far: %lu\n", dropped_packets);
            fflush(stdout);
        }
    }
    return 0;
}

int main(int argc, char **argv) {
    int ret;
    uint16_t port_id = 0;

    printf("Initializing EAL...\n");
    ret = rte_eal_init(argc, argv);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "Cannot init EAL: %s\n", rte_strerror(ret));
    }
    printf("EAL initialized successfully\n");

    printf("Getting device info for port %u...\n", port_id);
    struct rte_eth_dev_info dev_info;
    ret = rte_eth_dev_info_get(port_id, &dev_info);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "Cannot get device info: port=%u, err=%d\n", port_id, ret);
    }
    char name[RTE_ETH_NAME_MAX_LEN];
    rte_eth_dev_get_name_by_port(port_id, name);
    printf("Using device: %s (PCI address: %s)\n", dev_info.driver_name, name);

    printf("Creating mbuf pool...\n");
    mbuf_pool = rte_pktmbuf_pool_create("MBUF_POOL", NUM_MBUFS,
                                        MBUF_CACHE_SIZE, 0, MBUF_SIZE,
                                        rte_socket_id());
    if (mbuf_pool == NULL) {
        rte_exit(EXIT_FAILURE, "Cannot create mbuf pool: %s\n", rte_strerror(rte_errno));
    }
    printf("MBUF pool created with buffer size %u bytes\n", MBUF_SIZE);

    if (rte_eth_dev_count_avail() == 0) {
        rte_exit(EXIT_FAILURE, "No Ethernet ports available\n");
    }
    printf("Found %u available Ethernet ports\n", rte_eth_dev_count_avail());

    struct rte_eth_conf port_conf = {
        .rxmode = {
            .max_lro_pkt_size = MBUF_SIZE,
            .mtu = MAX_PACKET_SIZE - RTE_ETHER_HDR_LEN - RTE_ETHER_CRC_LEN,
            .offloads = RTE_ETH_RX_OFFLOAD_SCATTER,
        },
    };
    printf("Configuring device port %u...\n", port_id);
    ret = rte_eth_dev_configure(port_id, 1, 1, &port_conf);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "Cannot configure device: port=%u, err=%d\n", port_id, ret);
    }
    printf("Device configured successfully\n");

    struct rte_eth_rxconf rx_conf = {
        .rx_thresh = { .pthresh = 8, .hthresh = 8, .wthresh = 0 },
        .rx_free_thresh = 64,
        .offloads = RTE_ETH_RX_OFFLOAD_SCATTER,
    };
    printf("Setting up RX queue...\n");
    ret = rte_eth_rx_queue_setup(port_id, 0, RX_RING_SIZE,
                                 rte_eth_dev_socket_id(port_id), &rx_conf, mbuf_pool);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "Cannot setup RX queue: port=%u, err=%d\n", port_id, ret);
    }
    printf("RX queue setup complete\n");

    struct rte_eth_txconf tx_conf = {
        .tx_thresh = { .pthresh = 36, .hthresh = 0, .wthresh = 0 },
        .tx_free_thresh = 64,
    };
    printf("Setting up TX queue...\n");
    ret = rte_eth_tx_queue_setup(port_id, 0, TX_RING_SIZE,
                                 rte_eth_dev_socket_id(port_id), &tx_conf);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "Cannot setup TX queue: port=%u, err=%d\n", port_id, ret);
    }
    printf("TX queue setup complete\n");

    printf("Starting device port %u...\n", port_id);
    ret = rte_eth_dev_start(port_id);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "Cannot start device: port=%u, err=%d\n", port_id, ret);
    }
    printf("Port %u started successfully\n", port_id);

    printf("Enabling promiscuous mode on port %u...\n", port_id);
    rte_eth_promiscuous_enable(port_id);
    printf("Port %u in promiscuous mode\n", port_id);

    printf("Loading hash table...\n");
    if (create_hash_table_from_json("data.json") < 0) {
        rte_exit(EXIT_FAILURE, "Failed to create hash table from JSON\n");
    }
    printf("Hash table loaded successfully\n");

    printf("Running lcore_main directly in main thread...\n");
    lcore_main(NULL);  // Run directly instead of launching on a separate core

    printf("Cleaning up...\n");
    const void *next_key;
    void *next_data;
    uint32_t iter = 0;
    while (rte_hash_iterate(hash_table, &next_key, &next_data, &iter) >= 0) {
        free(next_data);
    }

    rte_eth_dev_stop(port_id);
    rte_eth_dev_close(port_id);
    rte_hash_free(hash_table);
    rte_eal_cleanup();
    printf("Cleanup complete\n");

    return 0;
}
