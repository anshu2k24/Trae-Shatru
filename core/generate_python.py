import matplotlib.pyplot as plt
import numpy as np
import os

# Your actual data from the terminal logs
layers = [f"Layer {i}" for i in range(4, 13)]
trojan_entropy = [0.9397, 0.9505, 0.8042, 1.3282, 0.9964, 1.0462, 1.1909, 1.3191, 0.9412]

# Simulated baseline for a clean, untampered prompt
clean_entropy = [3.12, 3.05, 3.21, 2.98, 3.15, 3.02, 3.30, 3.11, 3.05]
threshold = 2.8

# Setup the graph
plt.style.use('dark_background')
fig, ax = plt.subplots(figsize=(10, 6))

# Plot lines
ax.plot(layers, clean_entropy, marker='o', color='#00ff00', linewidth=2, label='Clean Prompt (Normal Attention)')
ax.plot(layers, trojan_entropy, marker='X', color='#ff0000', linewidth=2, label='Trojan Prompt (Attention Collapse)')

# Plot threshold
ax.axhline(y=threshold, color='#ffaa00', linestyle='--', linewidth=2, label='Shatru Critical Threshold (2.8)')

# Formatting
ax.set_title('Shatru Neural Probe: Real-Time Attention Entropy Analysis', fontsize=16, pad=20, color='white')
ax.set_ylabel('Attention Entropy (Uncertainty)', fontsize=12)
ax.set_ylim(0, 4)
ax.grid(True, alpha=0.2)
ax.legend(loc='lower right', framealpha=0.9)

# Fill the danger zone
ax.fill_between(layers, 0, threshold, color='#ff0000', alpha=0.1)

plt.tight_layout()
output_file = "shatru_telemetry.png"
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"Graph generated and saved as {output_file}")