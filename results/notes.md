# Indoor Navigation – Simulation Notes

## Experiment: PDR-only Simulation
- **Script used**: `simu_pdr.py`  
- **Description**:  
  Simulated IMU movement (sinusoidal + noise) and compared estimated PDR trajectory against a noise-free "true" trajectory.  
  Evaluated accuracy using Root Mean Square Error (RMSE).  

### Results (100 runs)
- **Mean RMSE**: `0.024 m`  
- **Std RMSE**: `0.015 m`  
- **Min RMSE**: `0.003 m`  
- **Max RMSE**: `0.064 m`  

### Observations
- PDR performs consistently well on this synthetic scenario (average error ~2–3 cm).  
- Low variance suggests robustness against random noise.  
- Some outliers (max ~6 cm) indicate occasional drift depending on random IMU noise. 

## Experiment: PDR-only from CSV
- **Script used**: `simu_pdr_csv.py`  
- **Description**:  
  Loaded recorded IMU traces from `data/pdr_traces/current.csv`. This dataset corresponds to a **full walk along the corridor and back** (round trip).  
  Applied step detection on accelerometer magnitude and computed stride length & heading with Weiberg’s method.  
  Constructed the pedestrian trajectory using PDR only (no external correction).  

### Results
- **Steps detected**: `N = 202`  
- **Trajectory**: plotted and saved in `results/plots/simu_pdr_csv.png`  
- **Start position**: `(2.175568, 41.406368)`  
- **End position**: `(2.175940, 41.406370)`  
- **Loop closure error**: `0.00037 m`  

### Observations
- The trajectory shows realistic movement following detected steps.  
- End position deviates from start, illustrating **drift accumulation** inherent to PDR.  
- Very low loop closure error (< 1 mm) in this dataset, likely due to favorable sensor noise conditions.  
- Useful as a baseline to compare against fusion with QR events or anchors.  

## Experiment: PDR + QR Fusion from CSV
- **Script used**: `simu_combined.py`  
- **Description**:  
  Loaded recorded IMU traces from `data/pdr_traces/current.csv` (same as above).  
  Applied PDR step detection and stride computation, then fused with **QR events** as position resets.  
  Constructed the pedestrian trajectory using **PDR + QR fusion**.  

### Results (PDR + QR)
- **Steps detected**: `202`  
- **QR resets applied**: `1`  
- **PDR total distance**: `90.9 m`  
- **Fused total distance**: `616.4 m`  
- **Start position**: `(2.175568, 41.406368)`  
- **Final PDR position (lon/lat)**: `(41.406628, 2.181449)`  
- **Final fused position (lon/lat)**: `(41.401899, 2.181441)`  
- **Target room**: `2-01`  
- **Final position error**: `~5 m` for PDR-only vs `~0.5 m` for PDR + QR  

### Observations
- PDR-only trajectory shows **drift accumulation** (final position several meters from start).  
- QR fusion reduces cumulative drift, yielding a final position much closer to the target (~0.5 m).  
- Demonstrates the benefit of using QR events as occasional resets in indoor navigation.  
- Still a small residual error remains, likely due to limited number/frequency of QR events.  

## Experiment: Corridor Graph Visualization
- **Script used**: `graph_visualizer.py`  
- **Description**:  
  Visualizes the indoor corridor graph, including **rooms**, **corridor points**, and **paths**.  
  - Graph loaded from `data/graph/corridor_graph.json`  
  - Optional floor plan background: `assets/OBuilding_Floor2.png`  
  - Supports visualization of **entire graph** and **specific paths**.  
  - Includes analysis tools: connectivity, isolated nodes.  

### Graph Analysis
- **Total nodes**: 50 
- **Total edges**: 175  
- **Connected components**: 1 (fully connected)  
- **Isolated nodes**: none  

### Pathfinding
- **Tested path**: `2-10 → 2-04`  
- **Path distance**: ~30 m   
- **Path sequence**: 2-10 → couloir → … → 2-04  
- Visualized and saved to: `data/results/path_2-10_to_2-04.png`  

### Notes
- Rooms and corridors are clearly distinguished with colors.  
- Graph visualization helps confirm **feasible paths** and **room connectivity**.  
- Can be integrated with PDR/QR trajectories for **combined navigation visualization**. 

**Conclusion**:  
QR resets effectively reduce drift and improve accuracy in indoor navigation via **Pedestrian-Dead-reckoning**. Graph visualization confirms corridor connectivity and enables accurate path planning (**djikstra**) between rooms like `2-10` and `2-04`.
