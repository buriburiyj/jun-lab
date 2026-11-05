import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

os.makedirs('/home/runner/ws/out', exist_ok=True)

compressors = ['zstd-1', 'zstd-22', 'lz4', 'lz4hc-9', 'lzf-1', 'fastlz-2', 'brotli-8', 'lzo1x-999']
compr_speed = [481, 10.9, 883, 14.4, 477, 450, 97.9, 3.23]
decompr_speed = [1418, 5637, 3153, 6389, 699, 894, 1320, 1099]
ratio = [20.82, 4.73, 40.64, 21.50, 33.72, 33.74, 5.79, 22.14]

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

axes[0].bar(compressors, compr_speed, color='steelblue')
axes[0].set_title('Compression speed (MB/s)')
axes[0].set_ylabel('MB/s')
axes[0].tick_params(axis='x', rotation=45)
for i, v in enumerate(compr_speed):
    axes[0].text(i, v + 10, f'{v}', ha='center', fontsize=8)

axes[1].bar(compressors, ratio, color='darkorange')
axes[1].set_title('Compression ratio (original/compressed)')
axes[1].set_ylabel('ratio (higher = less compression)')
axes[1].tick_params(axis='x', rotation=45)
for i, v in enumerate(ratio):
    axes[1].text(i, v + 0.5, f'{v:.2f}', ha='center', fontsize=8)

plt.tight_layout()
plt.savefig('/home/runner/ws/out/compression_bench.png', dpi=150)
print('saved /home/runner/ws/out/compression_bench.png')