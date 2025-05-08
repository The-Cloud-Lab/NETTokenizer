import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import argparse


def main(csv_file):
    df = pd.read_csv(csv_file)
    df['rps'] = pd.to_numeric(df['rps'], errors='coerce')
    df['tps'] = pd.to_numeric(df['tps'], errors='coerce')

    agg = df.groupby(['tokenizer', 'engine'])[['rps', 'tps']].mean().reset_index()

    rps_pivot = agg.pivot(index='tokenizer', columns='engine', values='rps')
    tps_pivot = agg.pivot(index='tokenizer', columns='engine', values='tps')

    engines = ['CPU', 'DPDK']
    colors = {'CPU': '#1f77b4', 'DPDK': '#ff7f0e'}
    width = 0.35
    x = np.arange(len(rps_pivot.index))

    plt.figure(figsize=(10,6))
    for i, engine in enumerate(engines):
        plt.bar(x + (i - 0.5)*width, rps_pivot[engine], width=width, label=engine, color=colors[engine])
    plt.xticks(x, rps_pivot.index)
    plt.xlabel('Tokenizer')
    plt.ylabel('Requests per Second (RPS)')
    plt.title('Average RPS by Tokenizer (CPU vs DPDK)')
    plt.legend()
    plt.tight_layout()
    plt.savefig('grouped_rps_by_tokenizer.png')
    plt.show()

    plt.figure(figsize=(10,6))
    for i, engine in enumerate(engines):
        plt.bar(x + (i - 0.5)*width, tps_pivot[engine], width=width, label=engine, color=colors[engine])
    plt.xticks(x, tps_pivot.index)
    plt.xlabel('Tokenizer')
    plt.ylabel('Tokens per Second (TPS)')
    plt.title('Average TPS by Tokenizer (CPU vs DPDK)')
    plt.legend()
    plt.tight_layout()
    plt.savefig('grouped_tps_by_tokenizer.png')
    plt.show()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Plot grouped RPS & TPS bar charts (CPU vs DPDK per tokenizer)"
    )
    parser.add_argument(
        '--csv', type=str, default='throughput_results.csv',
        help='Path to throughput_results.csv'
    )
    args = parser.parse_args()
    main(args.csv)
