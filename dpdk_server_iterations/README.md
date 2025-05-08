# Tokenizer Server Iteration Changelog

## tokenizer\_1.c

**Initial Version**

* Basic character-level tokenizer over UDP using DPDK.
* Processes single `sentence` field from JSON.
* Creates response JSON with token array and replies via UDP.
* Single-core support with hardcoded port handling.

## tokenizer\_2.c

**Stability + Cleanup**

* Removed verbose debug prints.
* Uses integer casting (`(void *)(uintptr_t)value`) to avoid dynamic memory allocation for hash table values.
* Adds MAC stats logging every fixed interval.
* Simplified payload parsing with no UDP header checks.

## tokenizer\_3.c

**Batch Tokenization Support**

* Introduced `texts` array support in JSON input.
* Added `[CLS]` and `[SEP]` token boundaries.
* Generates `input_ids` and `attention_mask` for each batch input.
* Added support for large packet sizes and extended sequence length.
* Improved error logging and packet validation.

## tokenizer\_4.c

**Multicore + Concurrency**

* Added per-core UDP port logic (`port = 67 + core_id`).
* Introduced `rte_spinlock_t` to protect hash table during batch tokenization.
* Further improved buffer sizing and logging.
* Each core independently processes its assigned stream of packets.

## tokenizer\_5.c

**Performance Logging**

* Added tokenization time measurement using `rte_get_timer_cycles()`.
* Logs batch size and latency to a CSV-compatible log file.
* Refined `tokenize_text()` logic for efficiency.
* Added token counting via space-delimited splitting.

## tokenizer\_6.c

**Full Parallelization with RSS Queues**

* Uses Receive Side Scaling (RSS) to distribute packets across cores.
* Each lcore independently processes its own RX/TX queue.
* Compact `tokenize()` function with fixed buffer reuse.
* Response built as a space-separated string of token IDs.
* Removes JSON parsing entirely for lower latency.
