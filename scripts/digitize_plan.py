"""
Interactive tool to digitize coordinates from a floor plan image.

Usage:
    python digitize_plan.py --image path/to/plan.png \
        --ref "<lat1,long1>" "<lat2,long2>"

The `--ref` flag takes two real-world points (in meters) corresponding
to the first two clicks you make on the image.
"""

import matplotlib
matplotlib.use('Qt5Agg')
import argparse
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

def parse_args():
    parser = argparse.ArgumentParser(
        description="Digitize real-world coordinates from a plan image"
    )
    parser.add_argument(
        "--image", "-i",
        required=True,
        help="Path to the floor plan image (PNG/JPG/TIFF)"
    )
    parser.add_argument(
        "--ref", "-r",
        required=True,
        nargs=2,
        metavar="X,Y",
        help=(
            "Two reference points in real-world coords, e.g. "
            "'0,0' '10,0' (meters). First click maps to the first point, "
            "second click to the second."
        )
    )
    return parser.parse_args()

def main():
    args = parse_args()

    # Load image
    img = Image.open(args.image)
    fig, ax = plt.subplots()
    ax.imshow(img)
    ax.set_title("Click on reference point A (first), then B (second)")
    
    # Parse real-world reference points
    real_pts = np.array([list(map(float, p.split(","))) for p in args.ref])

    # 1) Get pixel coordinates of A and B
    pix_pts = np.array(plt.ginput(2, timeout=-1))
    plt.close(fig)

    # Compute uniform scale (assumes no rotation/skew)
    delta_real = real_pts[1] - real_pts[0]
    delta_pix  = pix_pts[1]  - pix_pts[0]
    scale_x = delta_real[0] / delta_pix[0]
    scale_y = delta_real[1] / delta_pix[1]
    # If plan may be rotated, you could compute a full affine; here we assume axes aligned.
    tx = real_pts[0,0] - pix_pts[0,0] * scale_x
    ty = real_pts[0,1] - pix_pts[0,1] * scale_y

    print(f"Computed transform:\n"
          f"  X_real = X_pix * {scale_x:.6f} + {tx:.6f}\n"
          f"  Y_real = Y_pix * {scale_y:.6f} + {ty:.6f}")

    # 2) Digitize arbitrary points
    fig, ax = plt.subplots()
    ax.imshow(img)
    ax.set_title("Click any points to measure (right-click or ESC to finish)")
    pts = np.array(plt.ginput(n=-1, timeout=0, show_clicks=True))
    plt.close(fig)

    # 3) Convert pixel points to real-world coordinates
    real_meas = np.empty_like(pts)
    real_meas[:,0] = pts[:,0] * scale_x + tx
    real_meas[:,1] = pts[:,1] * scale_y + ty

    # 4) Print results
    print("\nDigitized points (real-world coordinates):")
    for i, (x, y) in enumerate(real_meas, start=1):
        print(f"  Point {i:2d}: X = {x:.6f} , Y = {y:.6f}")

if __name__ == "__main__":
    main()
