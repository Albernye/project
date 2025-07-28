import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from algorithms.fusion import fuse, reset_kalman

# Charge et nettoie
df = pd.read_csv("data/final_sensor_log.csv")
df['dt'] = df['timestamp'].diff().fillna(0)

# Interpole les accéléros manquants
df[['ACCE_X','ACCE_Y','ACCE_Z']] = df[['ACCE_X','ACCE_Y','ACCE_Z']].ffill().bfill()

# Calcule la PDR (double intégration)
df['vx'] = (df['ACCE_X'] * df['dt']).cumsum()
df['vy'] = (df['ACCE_Y'] * df['dt']).cumsum()
x0, y0 = df.loc[0, ['POSI_X','POSI_Y']]
df['pdr_X'] = x0 + (df['vx'] * df['dt']).cumsum()
df['pdr_Y'] = y0 + (df['vy'] * df['dt']).cumsum()

# Prépare Kalman
reset_kalman()
estimates = []

for _, row in df.iterrows():
    pdr = (row['pdr_X'], row['pdr_Y'], 2)
    fp  = (row['POSI_X'], row['POSI_Y'], 2)

    est = fuse(pdr, fp, room=None)
    estimates.append(est[:2])

estimates = np.array(estimates)

# Trace tout
plt.figure(figsize=(8,6))
plt.plot(df['POSI_X'], df['POSI_Y'], 'k-', label='Vraie POSI')
plt.plot(df['pdr_X'], df['pdr_Y'], '--', alpha=0.5, label='PDR brute')
plt.plot(estimates[:,0], estimates[:,1], 'g-', label='Estimation Kalman')
plt.legend()
plt.grid(True)
plt.show()
