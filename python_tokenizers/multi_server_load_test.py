import requests
import time
from lorem_text import lorem
import matplotlib.pyplot as plt
import numpy as np


CONFIG = {
    "iterations": 10,
    "use_log_scale": False,
    "check_monotonic": True,
    "show_trend_line": False,

    "models": [
        {
            "name": "msmarco_minilm",
            "sequence_length": 20,
            "base_batch_size": 10,
            "color": "green",
            "tokenize_url": "http://172.16.3.231:8012/tokenize",
            "infer_url": "http://172.16.3.98:8000/v2/models/msmarco_minilm/infer",
        },
        {
            "name": "tiny-bert",
            "sequence_length": 20,
            "base_batch_size": 10,
            "color": "red",
            "tokenize_url": "http://172.16.3.231:8010/tokenize",
            "infer_url": "http://172.16.3.98:8000/v2/models/bert_tiny/infer",
        },
        {
            "name": "paraphrase_minilm",
            "sequence_length": 20,
            "base_batch_size": 10,
            "color": "blue",
            "tokenize_url": "http://172.16.3.231:8011/tokenize",
            "infer_url": "http://172.16.3.98:8000/v2/models/paraphrase_minilm/infer",
        },
    ]
}


def generate_random_queries(batch_size, length):
    return [lorem.words(length) for _ in range(batch_size)]

def pad_or_truncate_sequences(input_ids, attention_mask, max_length):
    for i in range(len(input_ids)):
        input_ids[i] = input_ids[i][:max_length]
        attention_mask[i] = attention_mask[i][:max_length]
        while len(input_ids[i]) < max_length:
            input_ids[i].append(0)
            attention_mask[i].append(0)
    return input_ids, attention_mask

def call_tokenize_api(texts, url):
    payload = {"texts": texts}
    start_time = time.time()
    response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
    tokenization_time = time.time() - start_time

    if response.status_code == 200:
        result = response.json()
        input_ids = result.get('input_ids')
        attention_mask = result.get('attention_mask')
        return {"input_ids": input_ids, "attention_mask": attention_mask}, tokenization_time
    else:
        print(f"Tokenization request failed: {response.status_code}")
        return None, tokenization_time

def call_infer_api(batch_input_ids, batch_attention_mask, url):
    batch_size = len(batch_input_ids)
    token_len = len(batch_input_ids[0])
    payload = {
        "inputs": [
            {
                "name": "input_ids",
                "datatype": "INT64",
                "shape": [batch_size, token_len],
                "data": batch_input_ids,
            },
            {
                "name": "attention_mask",
                "datatype": "INT64",
                "shape": [batch_size, token_len],
                "data": batch_attention_mask,
            },
        ],
        "batch_size": batch_size,
    }

    start_time = time.time()
    response = requests.post(url, headers={"Content-Type": "application/json"}, json=payload)
    inference_time = time.time() - start_time

    if response.status_code == 200:
        return response.json(), inference_time
    else:
        print(f"Inference request failed: {response.status_code}")
        return None, inference_time

def check_monotonicity(times, label):
    for i in range(1, len(times)):
        if times[i] is not None and times[i - 1] is not None and times[i] < times[i - 1]:
            print(f"⚠️  Warning: {label} time decreased from batch {i} to {i + 1}.")

def test_model(model):
    model_name = model["name"]
    tokenize_url = model["tokenize_url"]
    infer_url = model["infer_url"]
    sequence_length = model["sequence_length"]
    base_batch_size = model["base_batch_size"]

    tokenization_times = []
    inference_times = []
    batch_sizes = []

    for i in range(1, CONFIG["iterations"] + 1):
        batch_size = base_batch_size * i
        batch_sizes.append(batch_size)
        batch_texts = generate_random_queries(batch_size, sequence_length)

        print(f"[{model_name}] Iteration {i}, Batch size = {batch_size}")

        tokenization_result, tok_time = call_tokenize_api(batch_texts, tokenize_url)
        if tokenization_result:
            batch_input_ids = tokenization_result['input_ids']
            batch_attention_mask = tokenization_result['attention_mask']
            batch_input_ids, batch_attention_mask = pad_or_truncate_sequences(batch_input_ids, batch_attention_mask, sequence_length)

            _, inf_time = call_infer_api(batch_input_ids, batch_attention_mask, infer_url)
            tokenization_times.append(tok_time)
            inference_times.append(inf_time)
            print(f"    Tokenization: {tok_time:.3f}s, Inference: {inf_time:.3f}s")
        else:
            print("    Skipping due to tokenization failure.")
            tokenization_times.append(None)
            inference_times.append(None)

    if CONFIG["check_monotonic"]:
        check_monotonicity(tokenization_times, f"{model_name} - Tokenization")

    return [bs * sequence_length for bs in batch_sizes], tokenization_times, inference_times


fig, axs = plt.subplots(len(CONFIG["models"]), 1, figsize=(16, 6 * len(CONFIG["models"])), sharex=True, constrained_layout=False)

for idx, model in enumerate(CONFIG["models"]):
    name = model["name"]
    color = model.get("color", "gray")
    ax = axs[idx] if len(CONFIG["models"]) > 1 else axs

    token_counts, token_times, infer_times = test_model(model)

    x = np.arange(len(token_counts))
    ax.bar(x, token_times, width=0.4, color=color, label='Tokenization')
    ax.plot(x, infer_times, label='Inference (line)', marker='o', linestyle='--', color='black')

    ax.set_title(f"{name}", fontsize=16)
    ax.set_ylabel("Time (seconds)", fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels([str(tk) for tk in token_counts])
    ax.tick_params(axis='x', labelsize=12)
    ax.tick_params(axis='y', labelsize=12)
    ax.legend(loc="upper left", fontsize=12)
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)

axs[-1].set_xlabel("Number of Tokens", fontsize=16)
plt.suptitle("Tokenization and Inference Time Scaling per Model", fontsize=18, y=0.995)


plt.subplots_adjust(
    left=0.08,    
    right=0.96,   
    top=0.93,     
    bottom=0.07,  
    hspace=0.20  
)


plt.savefig("tokenization_inference_plot.png", bbox_inches='tight', dpi=300)