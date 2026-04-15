import json
import matplotlib.pyplot as plt
import pandas as pd

# 1. Carga de datos
with open('trainer_state.json', 'r') as f:
    data = json.load(f)

# 2. Extraer Precisión y Loss
history = [log for log in data['log_history'] if 'mean_token_accuracy' in log]
steps = [log['step'] for log in history]
acc = [log['mean_token_accuracy'] for log in history]
loss = [log['loss'] for log in history]

# Crear DataFrame para suavizar
df = pd.DataFrame({'step': steps, 'accuracy': acc, 'loss': loss})
df['acc_smooth'] = df['accuracy'].rolling(window=30).mean()
df['loss_smooth'] = df['loss'].rolling(window=30).mean()

# 3. Gráfica Profesional
fig, ax1 = plt.subplots(figsize=(10, 6))

# Eje 1: Loss
ax1.set_xlabel('Training Steps')
ax1.set_ylabel('Loss', color='tab:red')
ax1.plot(df['step'], df['loss_smooth'], color='tab:red', linewidth=2, label='Train Loss')
ax1.tick_params(axis='y', labelcolor='tab:red')

# Eje 2: Accuracy
ax2 = ax1.twinx()
ax2.set_ylabel('Mean Token Accuracy', color='tab:blue')
ax2.plot(df['step'], df['acc_smooth'], color='tab:blue', linewidth=2, label='Accuracy')
ax2.tick_params(axis='y', labelcolor='tab:blue')

plt.title('Fine-Tuning Progress: Llama 3.1 8B (ReAct Tasks)')
fig.tight_layout()
plt.grid(True, alpha=0.2)
plt.show()