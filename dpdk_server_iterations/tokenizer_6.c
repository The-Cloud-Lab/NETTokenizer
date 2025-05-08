#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_mbuf.h>
#include <rte_hash.h>
#include <rte_jhash.h>
#include <cjson/cJSON.h>
#include <rte_cycles.h>
#include <rte_lcore.h>

#define RX_RING_SIZE 4096
#define TX_RING_SIZE 4096
#define NUM_MBUFS 65535
#define MBUF_CACHE_SIZE 512
#define BURST_SIZE 64
#define HASH_TABLE_SIZE 262144
#define MAX_SEQUENCE_LENGTH 512
#define MAX_PACKET_SIZE 8192
#define MBUF_SIZE (MAX_PACKET_SIZE + RTE_PKTMBUF_HEADROOM)

struct rte_hash *hash_table;
struct rte_mempool *mbuf_pool;
uint16_t port_id = 0;

int create_hash_table_from_json(const char *json_file) {
    FILE *file = fopen(json_file, "r");
    if (!file) return -1;
    fseek(file, 0, SEEK_END);
    long size = ftell(file);
    fseek(file, 0, SEEK_SET);
    char *data = malloc(size + 1);
    fread(data, 1, size, file);
    fclose(file);
    data[size] = '\0';

    cJSON *json = cJSON_Parse(data);
    if (!json) return -1;

    struct rte_hash_parameters hash_params = {
        .name = "token_hash",
        .entries = HASH_TABLE_SIZE,
        .key_len = 32,
        .hash_func = rte_jhash,
        .hash_func_init_val = 0
    };
    hash_table = rte_hash_create(&hash_params);
    if (!hash_table) return -1;

    cJSON *item;
    cJSON_ArrayForEach(item, json) {
        char *key = item->string;
        int value = item->valueint;
        char padded[32] = {0};
        memcpy(padded, key, strlen(key) > 32 ? 32 : strlen(key));
        int *val_ptr = malloc(sizeof(int));
        *val_ptr = value;
        rte_hash_add_key_data(hash_table, padded, val_ptr);
    }

    cJSON_Delete(json);
    free(data);
    return 0;
}

void tokenize(const char *text, int *ids, int *mask) {
    ids[0] = 101; mask[0] = 1;
    int pos = 1;
    for (int i = 0; text[i] && pos < MAX_SEQUENCE_LENGTH - 1; i++) {
        char key[32] = {text[i], 0};
        int *val;
        if (rte_hash_lookup_data(hash_table, key, (void**)&val) >= 0) {
            ids[pos] = *val;
            mask[pos++] = 1;
        }
    }
    ids[pos] = 102; mask[pos] = 1;
}

int lcore_main(void *arg) {
    uint16_t qid = *(uint16_t *)arg;
    struct rte_mbuf *rx_bufs[BURST_SIZE], *tx_bufs[BURST_SIZE];
    char resp_buf[MAX_PACKET_SIZE];

    

    while (1) {
        uint16_t nb_rx = rte_eth_rx_burst(port_id, qid, rx_bufs, BURST_SIZE);
        if (!nb_rx) continue;

        int tx_count = 0;
        for (int i = 0; i < nb_rx; i++) {
            struct rte_mbuf *m = rx_bufs[i];
            struct rte_ether_hdr *eth_hdr = rte_pktmbuf_mtod(m, struct rte_ether_hdr *);
            struct rte_udp_hdr *udp_hdr = (struct rte_udp_hdr *)(eth_hdr + 1);
            char *payload = (char *)(udp_hdr + 1);
            payload[rte_be_to_cpu_16(udp_hdr->dgram_len) - sizeof(*udp_hdr)] = 0;

            int ids[MAX_SEQUENCE_LENGTH] = {0}, mask[MAX_SEQUENCE_LENGTH] = {0};
            tokenize(payload, ids, mask);

            int offset = 0;
            for (int j = 0; j < MAX_SEQUENCE_LENGTH && ids[j]; j++)
                offset += sprintf(resp_buf + offset, "%d ", ids[j]);

            struct rte_mbuf *resp = rte_pktmbuf_alloc(mbuf_pool);
            if (!resp) continue;
            char *d = rte_pktmbuf_append(resp, sizeof(*eth_hdr) + sizeof(*udp_hdr) + offset);
            struct rte_ether_hdr *e = (struct rte_ether_hdr *)d;
            struct rte_udp_hdr *u = (struct rte_udp_hdr *)(e + 1);
            memcpy(e, eth_hdr, sizeof(*e));
            e->dst_addr = eth_hdr->src_addr;
            rte_eth_macaddr_get(port_id, &e->src_addr);
            u->src_port = udp_hdr->dst_port;
            u->dst_port = udp_hdr->src_port;
            u->dgram_len = rte_cpu_to_be_16(sizeof(*u) + offset);
            u->dgram_cksum = 0;
            memcpy((char *)(u + 1), resp_buf, offset);

            tx_bufs[tx_count++] = resp;
            rte_pktmbuf_free(m);
        }
        if (tx_count)
            rte_eth_tx_burst(port_id, qid, tx_bufs, tx_count);
    }
    return 0;
}

int main(int argc, char **argv) {
    rte_eal_init(argc, argv);

    uint16_t nb_ports = rte_eth_dev_count_avail();
    if (nb_ports == 0) {
        rte_exit(EXIT_FAILURE, "No Ethernet ports found. Is the NIC bound to DPDK?\n");
    }

    port_id = 0; // pick first
    printf("Detected %u DPDK ports\n", nb_ports);

     else {
            printf("Warning: Failed to get info for port %u
", i);
        }
    } else {
            printf("Warning: Failed to get info for port %u
", i);
        }
    } else {
            printf("Warning: Failed to get info for port %u
", i);
        }
    } else {
            printf("Warning: Failed to get info for port %u
", i);
        }
    }

    mbuf_pool = rte_pktmbuf_pool_create("MBUF_POOL", NUM_MBUFS, MBUF_CACHE_SIZE, 0, MBUF_SIZE, rte_socket_id());

    unsigned nb_queues = rte_lcore_count();
    struct rte_eth_conf port_conf = {
        .rxmode = {
            .mq_mode = RTE_ETH_MQ_RX_RSS
        },
        .rx_adv_conf = {
            .rss_conf = {
                .rss_hf = RTE_ETH_RSS_UDP
            }
        }
    };
    rte_eth_dev_configure(port_id, nb_queues, nb_queues, &port_conf);

    for (unsigned q = 0; q < nb_queues; q++) {
        rte_eth_rx_queue_setup(port_id, q, RX_RING_SIZE, rte_eth_dev_socket_id(port_id), NULL, mbuf_pool);
        rte_eth_tx_queue_setup(port_id, q, TX_RING_SIZE, rte_eth_dev_socket_id(port_id), NULL);
    }

    rte_eth_dev_start(port_id);
    rte_eth_promiscuous_enable(port_id);

    if (!rte_eth_dev_is_valid_port(port_id)) {
        rte_exit(EXIT_FAILURE, "Port %u is not valid\n", port_id);
    }

    if (create_hash_table_from_json("data.json") < 0)
        rte_exit(EXIT_FAILURE, "Failed to load vocab\n");

    uint16_t qid_array[RTE_MAX_LCORE];
    unsigned qidx = 0;
    unsigned lcore_id;
    RTE_LCORE_FOREACH_WORKER(lcore_id) {
        qid_array[qidx] = qidx;
        rte_eal_remote_launch(lcore_main, &qid_array[qidx], lcore_id);
        qidx++;
    }
    qid_array[qidx] = qidx;
    lcore_main(&qid_array[qidx]);

    rte_eal_cleanup();
    return 0;
}
