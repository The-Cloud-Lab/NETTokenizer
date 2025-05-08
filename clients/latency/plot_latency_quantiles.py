import numpy as np
import matplotlib.pyplot as plt
import os

def plot_quantiles(results_dict, title, filename):
    plt.figure(figsize=(12, 6))

    percentiles = np.linspace(0, 100, 101)

    for label, times in results_dict.items():
        times = np.array(times)
        times = times[times > 0] 
        quantile_vals = np.percentile(times, percentiles)
        plt.plot(percentiles, quantile_vals, marker='.', linestyle='-', label=label)

        p90_x = 90
        p99_x = 99
        p90_y = np.percentile(times, 90)
        p99_y = np.percentile(times, 99)
        plt.axvline(p90_x, color='gray', linestyle='--', linewidth=0.7)
        plt.axvline(p99_x, color='gray', linestyle='--', linewidth=0.7)
        plt.text(p90_x + 0.5, p90_y, f'{label} P90: {p90_y:.1f}µs', fontsize=7, rotation=0, va='bottom')
        plt.text(p99_x + 0.5, p99_y, f'{label} P99: {p99_y:.1f}µs', fontsize=7, rotation=0, va='bottom')

    plt.title(title)
    plt.xlabel("Percentile (%)")
    plt.ylabel("Tokenization Time (µs)")
    plt.grid(True, linestyle="--", linewidth=0.5)
    plt.legend(loc="upper left", fontsize=8)
    plt.tight_layout()
    plt.savefig(filename)
    print(f"Saved quantile plot: {filename}")

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
        plot_quantiles(results, "DPDK-GPT2 Tokenization Time by Percentile", "quantile_plot_DPDK_GPT2.png")
    else:
        print("No valid data to plot.")
