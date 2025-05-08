import numpy as np
import matplotlib.pyplot as plt
import os

def plot_combined_cdf(results_dict, title, filename):
    plt.figure(figsize=(12, 6))

    for label, times in results_dict.items():
        times = np.array(times)
        times = times[times > 0]
        sorted_times = np.sort(times)
        cumulative = np.arange(1, len(sorted_times) + 1) / len(sorted_times)

        plt.plot(sorted_times, cumulative, marker='.', linestyle='-', label=label)

        p90 = np.percentile(sorted_times, 90)
        p99 = np.percentile(sorted_times, 99)
        plt.axvline(p90, linestyle='--', color='gray', linewidth=0.7)
        plt.axvline(p99, linestyle='--', color='gray', linewidth=0.7)
        plt.text(p90, 0.05, f'{label} P90: {p90:.1f}µs', rotation=90, fontsize=7, va='bottom')
        plt.text(p99, 0.05, f'{label} P99: {p99:.1f}µs', rotation=90, fontsize=7, va='bottom')

    plt.axhline(0.9, linestyle='--', color='red', linewidth=0.5, label='90% Threshold')
    plt.axhline(0.99, linestyle='--', color='blue', linewidth=0.5, label='99% Threshold')

    plt.title(title)
    plt.xlabel("Tokenization Time (µs)")
    plt.ylabel("Cumulative Fraction of Requests")
    plt.grid(True, linestyle="--", linewidth=0.5)
    plt.legend(loc="lower right", fontsize=8)
    plt.tight_layout()
    plt.savefig(filename)
    print(f"Saved combined CDF: {filename}")

if __name__ == "__main__":
    results = {}

    for batch in [25, 50, 75]:
        filename = f"DPDK_GPT2_{batch}T.npy"
        label = f"DPDK-GPT2-{batch}T"
        if os.path.exists(filename):
            results[label] = np.load(filename)
        else:
            print(f"⚠️ Missing: {filename}")

    if results:
        plot_combined_cdf(results, "DPDK-GPT2 Combined CDF (25T, 50T, 75T)", "cdf_combined_DPDK_GPT2.png")
    else:
        print("No valid data to plot.")
