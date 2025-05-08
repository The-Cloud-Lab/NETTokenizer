#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_mbuf.h>
#include <rte_hash.h>
#include <rte_jhash.h>
#include <cjson/cJSON.h>

#define RX_RING_SIZE 1024
#define TX_RING_SIZE 1024
#define NUM_MBUFS 8191
#define MBUF_CACHE_SIZE 250
#define BURST_SIZE 32
#define HASH_TABLE_SIZE 65536

struct rte_hash *hash_table;
struct rte_mempool *mbuf_pool;

int create_hash_table_from_json(const char *json_file) {
    FILE *file = fopen(json_file, "r");
    if (!file) {
        printf("Error: Could not open JSON file '%s'.\n", json_file);
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
        printf("Error: Failed to parse JSON.\n");
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
        printf("Error: Failed to create hash table.\n");
        cJSON_Delete(json);
        free(json_data);
        return -1;
    }

    cJSON *item;
    cJSON_ArrayForEach(item, json) {
        char *key = item->string;
        int value = item->valueint;
        char padded_key[32] = {0};
        size_t key_len = strlen(key);
        if (key_len > 32) key_len = 32;
        memcpy(padded_key, key, key_len);

        int ret = rte_hash_add_key_data(hash_table, padded_key, (void *)(uintptr_t)value);
        if (ret < 0) {
            printf("Error: Failed to add key '%s' to hash table (ret=%d).\n", key, ret);
        }
    }

    cJSON_Delete(json);
    free(json_data);
    return 0;
}

void tokenize_sentence(const char *sentence, int *tokens, int *token_count) {
    *token_count = 0;
    for (int i = 0; i < strlen(sentence); i++) {
        char key[2] = {sentence[i], '\0'};
        char padded_key[32] = {0};
        size_t key_len = strlen(key);
        memcpy(padded_key, key, key_len);

        int *value = NULL;
        int ret = rte_hash_lookup_data(hash_table, padded_key, (void **)&value);
        if (ret >= 0 && value) {
            tokens[(*token_count)++] = *value;
        }
    }
}

static int lcore_main(__rte_unused void *arg) {
    uint16_t port_id = 0;
    struct rte_mbuf *bufs[BURST_SIZE];

    printf("Waiting for packets on port %u (core %u)...\n", port_id, rte_lcore_id());

    while (1) {
        uint16_t nb_rx = rte_eth_rx_burst(port_id, 0, bufs, BURST_SIZE);
        if (nb_rx > 0) {
            printf("Received %u packets on core %u\n", nb_rx, rte_lcore_id());
            for (int i = 0; i < nb_rx; i++) {
                struct rte_mbuf *m = bufs[i];
                struct rte_ether_hdr *eth_hdr = rte_pktmbuf_mtod(m, struct rte_ether_hdr *);

                char *payload = (char *)(eth_hdr + 1);
                int payload_len = m->pkt_len - sizeof(struct rte_ether_hdr);

                printf("Received Data: %.*s\n", payload_len, payload);

                cJSON *json = cJSON_Parse(payload);
                if (!json) {
                    printf("Error parsing JSON.\n");
                    rte_pktmbuf_free(m);
                    continue;
                }

                cJSON *sentence_json = cJSON_GetObjectItemCaseSensitive(json, "sentence");
                if (!sentence_json || !cJSON_IsString(sentence_json)) {
                    cJSON_Delete(json);
                    rte_pktmbuf_free(m);
                    continue;
                }

                const char *sentence = sentence_json->valuestring;
                int tokens[256];
                int token_count = 0;
                tokenize_sentence(sentence, tokens, &token_count);

                cJSON *response_json = cJSON_CreateObject();
                cJSON *tokens_array = cJSON_CreateIntArray(tokens, token_count);
                cJSON_AddItemToObject(response_json, "tokens", tokens_array);
                char *response_str = cJSON_PrintUnformatted(response_json);

                printf("Response: %s\n", response_str);

                struct rte_mbuf *response_mbuf = rte_pktmbuf_alloc(mbuf_pool);
                if (!response_mbuf) {
                    cJSON_Delete(json);
                    cJSON_Delete(response_json);
                    free(response_str);
                    rte_pktmbuf_free(m);
                    continue;
                }

                size_t response_len = strlen(response_str) + 1;
                if (rte_pktmbuf_append(response_mbuf, sizeof(struct rte_ether_hdr) + response_len) == NULL) {
                    rte_pktmbuf_free(response_mbuf);
                    cJSON_Delete(json);
                    cJSON_Delete(response_json);
                    free(response_str);
                    rte_pktmbuf_free(m);
                    continue;
                }

                struct rte_ether_hdr *resp_eth_hdr = rte_pktmbuf_mtod(response_mbuf, struct rte_ether_hdr *);
                rte_ether_addr_copy(&eth_hdr->src_addr, &resp_eth_hdr->dst_addr);  // Fixed typo
                rte_eth_macaddr_get(port_id, &resp_eth_hdr->src_addr);
                resp_eth_hdr->ether_type = rte_cpu_to_be_16(0x88B5);

                char *response_data = (char *)(resp_eth_hdr + 1);
                strcpy(response_data, response_str);

                response_mbuf->data_len = sizeof(struct rte_ether_hdr) + response_len;
                response_mbuf->pkt_len = sizeof(struct rte_ether_hdr) + response_len;

                uint16_t nb_tx = rte_eth_tx_burst(port_id, 0, &response_mbuf, 1);
                if (nb_tx < 1) {
                    printf("Failed to send response on core %u\n", rte_lcore_id());
                    rte_pktmbuf_free(response_mbuf);
                }

                cJSON_Delete(json);
                cJSON_Delete(response_json);
                free(response_str);
                rte_pktmbuf_free(m);
            }
        } else {
            static int count = 0;
            if (++count % 10000000 == 0 && rte_lcore_id() == 0) {
                struct rte_eth_stats stats;
                rte_eth_stats_get(port_id, &stats);
                printf("Core %u: RX packets=%lu, RX errors=%lu, RX dropped=%lu\n",
                       rte_lcore_id(), stats.ipackets, stats.ierrors, stats.imissed);
            }
        }
    }
    return 0;
}

int main(int argc, char **argv) {
    int ret;
    unsigned lcore_id;
    uint16_t port_id = 0;

    ret = rte_eal_init(argc, argv);
    if (ret < 0) rte_panic("Cannot init EAL\n");

    struct rte_eth_dev_info dev_info;
    ret = rte_eth_dev_info_get(port_id, &dev_info);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "Cannot get device info: port=%u, err=%d\n", port_id, ret);
    }
    char name[RTE_ETH_NAME_MAX_LEN];
    rte_eth_dev_get_name_by_port(port_id, name);
    printf("Using device: %s (PCI address: %s)\n", dev_info.driver_name, name);

    struct rte_ether_addr addr;
    rte_eth_macaddr_get(port_id, &addr);
    printf("Port %u MAC: %02x:%02x:%02x:%02x:%02x:%02x\n",
           port_id, addr.addr_bytes[0], addr.addr_bytes[1], addr.addr_bytes[2],
           addr.addr_bytes[3], addr.addr_bytes[4], addr.addr_bytes[5]);

    mbuf_pool = rte_pktmbuf_pool_create("MBUF_POOL", NUM_MBUFS,
                                        MBUF_CACHE_SIZE, 0, RTE_MBUF_DEFAULT_BUF_SIZE,
                                        rte_socket_id());
    if (mbuf_pool == NULL) {
        rte_exit(EXIT_FAILURE, "Cannot create mbuf pool\n");
    }

    if (rte_eth_dev_count_avail() == 0) {
        rte_exit(EXIT_FAILURE, "No Ethernet ports available\n");
    }

    struct rte_eth_conf port_conf = {
        .rxmode = {
            .max_lro_pkt_size = RTE_ETHER_MAX_LEN,
        },
    };
    ret = rte_eth_dev_configure(port_id, 1, 1, &port_conf);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "Cannot configure device: port=%u, err=%d\n", port_id, ret);
    }

    ret = rte_eth_rx_queue_setup(port_id, 0, RX_RING_SIZE,
                                 rte_eth_dev_socket_id(port_id), NULL, mbuf_pool);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "Cannot setup RX queue: port=%u, err=%d\n", port_id, ret);
    }

    ret = rte_eth_tx_queue_setup(port_id, 0, TX_RING_SIZE,
                                 rte_eth_dev_socket_id(port_id), NULL);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "Cannot setup TX queue: port=%u, err=%d\n", port_id, ret);
    }

    ret = rte_eth_dev_start(port_id);
    if (ret < 0) {
        rte_exit(EXIT_FAILURE, "Cannot start device: port=%u, err=%d\n", port_id, ret);
    }

    struct rte_eth_link link;
    (void)rte_eth_link_get_nowait(port_id, &link);
    if (link.link_status == RTE_ETH_LINK_DOWN) {
        printf("Port %u link is down\n", port_id);
    } else {
        printf("Port %u link is up (speed %u Mbps, %s)\n",
               port_id, link.link_speed, link.link_duplex == RTE_ETH_LINK_FULL_DUPLEX ? "full-duplex" : "half-duplex");
    }

    rte_eth_promiscuous_enable(port_id);

    if (create_hash_table_from_json("data.json") < 0) {
        rte_exit(EXIT_FAILURE, "Failed to create hash table from JSON.\n");
    }

    RTE_LCORE_FOREACH_WORKER(lcore_id) {
        rte_eal_remote_launch(lcore_main, NULL, lcore_id);
    }

    lcore_main(NULL);

    rte_eal_mp_wait_lcore();

    rte_eth_dev_stop(port_id);
    rte_eth_dev_close(port_id);
    rte_hash_free(hash_table);
    rte_eal_cleanup();

    return 0;
}