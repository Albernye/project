"""
PDR + QR fusion simulation
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from algorithms.PDR import (
    step_detection_accelerometer,
    weiberg_stride_length_heading_position
)
from algorithms.fingerprint import set_origin, ll_to_local
from services.utils import read_json_safe
from config import (
    DEFAULT_POSXY, SIM_DURATION, SIM_FS, QR_EVENTS_FILE,
    PDR_TRACE, FP_CURRENT, ROOM_POS_CSV, USE_SIMULATED_IMU
)
from pathlib import Path
import re

def parse_qr_timestamp(timestamp_str):
    """
    Parse QR timestamp with custom format handling
    """
    try:
        # Remove the 'Z' at the end and handle the timezone
        cleaned = timestamp_str.replace('Z', '').replace('+00:00', '')
        # Parse as regular datetime
        return pd.to_datetime(cleaned)
    except:
        try:
            # Alternative parsing
            return pd.to_datetime(timestamp_str, format='%Y-%m-%dT%H:%M:%S.%f+00:00Z')
        except:
            # Extract just the seconds part from '1970-01-01T00:00:03.997600+00:00Z'
            match = re.search(r'T00:00:(\d+\.\d+)', timestamp_str)
            if match:
                seconds = float(match.group(1))
                return pd.Timestamp.fromtimestamp(seconds)
            else:
                return None

def run_combined_simple(merged_csv_path: str, qr_json_path: str):
    """
    Simple PDR + QR fusion with fixed timestamp handling
    """
    
    # 1) Initialize origin
    origin_lon, origin_lat = DEFAULT_POSXY
    set_origin(origin_lon, origin_lat)
    print(f"Origin set to: {origin_lon}, {origin_lat}")
    
    # 2) Load merged CSV for PDR
    print("Loading merged CSV...")
    df = pd.read_csv(merged_csv_path)
    accel = df[['ACCE_X','ACCE_Y','ACCE_Z']].values
    gyro = df[['GYRO_X','GYRO_Y','GYRO_Z']].values
    times = df['timestamp'].values
    
    # Calculate sampling frequency
    fs = 1.0 / np.mean(np.diff(times))
    print(f"Sampling frequency: {fs:.2f} Hz, Total samples: {len(df)}")
    
    # 3) Load QR events with better timestamp parsing
    print("Loading QR events...")
    qr_events = read_json_safe(Path(qr_json_path))
    if not qr_events:
        print("⚠️ No QR events found, running PDR-only")
        qr_events = []
    else:
        print(f"Found {len(qr_events)} QR events")
    
    # Convert QR events to local coordinates with fixed timestamps
    qr_resets = []
    for ev in qr_events:
        try:
            # Use custom timestamp parser
            parsed_time = parse_qr_timestamp(ev['timestamp'])
            if parsed_time is None:
                print(f"⚠️ Could not parse timestamp: {ev['timestamp']}")
                continue
                
            timestamp = parsed_time.timestamp()
            lon, lat = ev['position']
            x, y = ll_to_local(lon, lat)
            qr_resets.append({
                'timestamp': timestamp,
                'x': x,
                'y': y,
                'room': ev.get('room', 'unknown')
            })
            print(f"✅ QR event: {ev['room']} at t={timestamp:.1f}s -> ({x:.1f}, {y:.1f})")
        except Exception as e:
            print(f"⚠️ Skipping QR event {ev.get('room', 'unknown')}: {e}")
    
    qr_resets.sort(key=lambda x: x['timestamp'])
    print(f"Valid QR resets: {len(qr_resets)}")
    
    # 4) Run PDR step detection once
    print("Running PDR step detection...")
    magnitude = np.linalg.norm(accel, axis=1)
    t = np.arange(len(magnitude)) / fs
    
    num_steps, step_indices, stance = step_detection_accelerometer(
        magnitude, t, plot=False
    )
    print(f"Detected {num_steps} steps")
    
    if num_steps == 0:
        print("⚠️ No steps detected, creating static trajectory")
        trajectory = np.zeros((len(df), 2))
    else:
        # 5) Compute PDR trajectory once
        print("Computing PDR trajectory...")
        thetas, step_positions = weiberg_stride_length_heading_position(
            accel, gyro, t, step_indices, stance, ver=False, idx_fig=0
        )
        
        print(f"PDR trajectory: {len(step_positions)} positions")
        print(f"PDR start: ({step_positions[0,0]:.2f}, {step_positions[0,1]:.2f})")
        print(f"PDR end: ({step_positions[-1,0]:.2f}, {step_positions[-1,1]:.2f})")
        
        # 6) Interpolate PDR positions to all timestamps (SIMPLIFIED)
        trajectory = np.zeros((len(df), 2))
        
        # Simple linear interpolation based on sample index
        for i in range(len(df)):
            if len(step_positions) == 1:
                trajectory[i] = step_positions[0]
            else:
                # Map sample index to step index
                progress = i / (len(df) - 1) if len(df) > 1 else 0
                step_progress = progress * (len(step_positions) - 1)
                step_idx = int(step_progress)
                
                if step_idx >= len(step_positions) - 1:
                    trajectory[i] = step_positions[-1]
                else:
                    # Linear interpolation between steps
                    alpha = step_progress - step_idx
                    trajectory[i] = (1 - alpha) * step_positions[step_idx] + alpha * step_positions[step_idx + 1]
    
    # 7) Apply QR resets (SIMPLIFIED)
    print("Applying QR resets...")
    fused_trajectory = trajectory.copy()
    
    # Convert data timestamps to seconds for easier comparison
    data_times = pd.to_datetime(times).astype(np.int64) / 1e9
    
    for qr_reset in qr_resets:
        qr_time = qr_reset['timestamp']
        qr_x, qr_y = qr_reset['x'], qr_reset['y']
        
        # Find closest data point
        time_diffs = np.abs(data_times - qr_time)
        closest_idx = np.argmin(time_diffs)
        
        # Apply reset by calculating offset
        if closest_idx < len(fused_trajectory):
            current_pos = fused_trajectory[closest_idx]
            offset = np.array([qr_x, qr_y]) - current_pos
            
            # Apply offset to all subsequent positions
            fused_trajectory[closest_idx:] += offset
            
            print(f"QR reset {qr_reset['room']} at sample {closest_idx}: "
                  f"offset=({offset[0]:.2f}, {offset[1]:.2f})")
    
    # 8) Plot results
    plt.figure(figsize=(15, 10))
    
    # Plot 1: Main trajectory comparison
    plt.subplot(1, 3, 1)
    plt.plot(trajectory[:, 0], trajectory[:, 1], '--b', alpha=0.7, linewidth=1, label='PDR only')
    plt.plot(fused_trajectory[:, 0], fused_trajectory[:, 1], '-r', linewidth=2, label='PDR + QR fused')
    
    # Mark QR reset points
    for qr_reset in qr_resets:
        plt.plot(qr_reset['x'], qr_reset['y'], 'go', markersize=6, alpha=0.8)
    
    # Mark start and end
    plt.plot(fused_trajectory[0, 0], fused_trajectory[0, 1], 'ks', markersize=8, label='Start')
    plt.plot(fused_trajectory[-1, 0], fused_trajectory[-1, 1], 'k*', markersize=12, label='End')
    
    plt.title('PDR + QR Fusion Trajectory')
    plt.xlabel('X (m)')
    plt.ylabel('Y (m)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.axis('equal')
    


    # Plot 2: Acceleration magnitude with detected steps
    plt.subplot(1, 3, 2)
    plt.plot(t[:5000], magnitude[:5000], 'b-', alpha=0.7, label='|Acceleration|')  # First 5000 samples
    for step_idx in step_indices:
        if step_idx < 5000:  # Only show steps in the displayed range
            plt.axvline(t[step_idx], color='r', alpha=0.5, linewidth=0.5)
    plt.title(f'Step Detection ({num_steps} total steps)')
    plt.xlabel('Time (s)')
    plt.ylabel('Acceleration (m/s²)')
    plt.grid(True, alpha=0.3)
    
    # Plot 3: QR events timeline
    plt.subplot(1, 3, 3)
    if qr_resets:
        qr_times = [qr['timestamp'] for qr in qr_resets]
        qr_x_pos = [qr['x'] for qr in qr_resets]
        qr_y_pos = [qr['y'] for qr in qr_resets]
        
        plt.scatter(qr_times, qr_x_pos, c='red', marker='o', label='QR X')
        plt.scatter(qr_times, qr_y_pos, c='blue', marker='s', label='QR Y')
        plt.title('QR Events Timeline')
        plt.xlabel('Time (s)')
        plt.ylabel('Position (m)')
        plt.legend()
    else:
        plt.text(0.5, 0.5, 'No QR events', ha='center', va='center', transform=plt.gca().transAxes)
        plt.title('QR Events Timeline')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Calculate and print statistics
    total_pdr_distance = np.sum(np.sqrt(np.sum(np.diff(trajectory, axis=0)**2, axis=1)))
    total_fused_distance = np.sum(np.sqrt(np.sum(np.diff(fused_trajectory, axis=0)**2, axis=1)))
    
    print(f"\n📊 Trajectory Statistics:")
    print(f"  Duration: {len(df)/fs:.1f}s ({len(df)/fs/60:.1f} min)")
    print(f"  Steps detected: {num_steps}")
    print(f"  QR resets applied: {len(qr_resets)}")
    print(f"  PDR total distance: {total_pdr_distance:.1f}m")
    print(f"  Fused total distance: {total_fused_distance:.1f}m")
    print(f"  Final PDR position: ({trajectory[-1,0]:.2f}, {trajectory[-1,1]:.2f})")
    print(f"  Final fused position: ({fused_trajectory[-1,0]:.2f}, {fused_trajectory[-1,1]:.2f})")
    
    plt.show()
    
    return fused_trajectory

if __name__ == "__main__":
    try:
        result = run_combined_simple("data/pdr_traces/current.csv", str(QR_EVENTS_FILE))
        print("✅ Simulation completed successfully!")
    except Exception as e:
        print(f"❌ Error running simulation: {e}")
        import traceback
        traceback.print_exc()