import numpy as np
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(4,4))

labels = ["Blind", "All-in-context", "React ICL 70B"]
means = [1.3957, 4.1532, 3.9447]
errs  = [0.1327, 0.1815, 0.1740]

x = np.arange(len(labels))

ax.bar(x, means, yerr=errs, capsize=4, color=["C0", "C1", "C2"])

ax.set_ylabel("Prometheus Score")
ax.set_xticks(x)
ax.set_xticklabels(labels)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.show()