import pandas as pd
import matplotlib.pyplot as plt

def plot_trajectory(file_path, label):
    data = pd.read_csv(file_path)
    plt.plot(data['longitude'], data['latitude'], label=label)

plt.figure(figsize=(12, 8))

# Tracer les trajectoires pour chaque fichier
plot_trajectory('data/processed/sample/route_1_representative_sample.csv', 'Route 1')
plot_trajectory('data/processed/sample/route_2_representative_sample.csv', 'Route 2')
plot_trajectory('data/processed/sample/route_3_representative_sample.csv', 'Route 3')

plt.title("Trajectoires Réelles")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.legend()
plt.grid(True)
plt.savefig('data/real_trajectories.png')
plt.show()
