"""
visual_tui.py — Live 8×8 text visualizer for VisionAssist sensor simulation
Displays smoothed ToF data (in meters) from sensor_processor in real time.

Works in any terminal (SSH, VS Code, or VNC).
Author: Geo & ChatGPT (2025)
"""

import os
import time
import math
from sensors import sensor_processor as sp

# === CONFIGURATION ===
REFRESH_HZ = 5        # how many times per second to refresh
SHOW_VALUES = True    # show numeric ToF values
USE_COLOR = True      # ANSI color shading
GRID_SIZE = 8


# === COLOR MAPPING ===
def get_color(val_m):
    """Map distance to color based on proximity."""
    if not USE_COLOR:
        return ""
    if val_m > 1.5:
        return "\033[92m"  # green
    elif val_m > 1.0:
        return "\033[93m"  # yellow
    elif val_m > 0.5:
        return "\033[91m"  # red
    else:
        return "\033[95m"  # magenta


def clear_screen():
    os.system("clear" if os.name == "posix" else "cls")


# === MAIN LOOP ===
def main():
    print("🧭 Visual TUI started — watching ToF data...")
    interval = 1.0 / REFRESH_HZ

    # Provide a placeholder frame so we always draw something
    frame = [1.5 for _ in range(GRID_SIZE * GRID_SIZE)]

    try:
        while True:
            # if sensor_processor has data, update frame
            if hasattr(sp, "last_tof_frame") and sp.last_tof_frame:
                frame = sp.last_tof_frame
            else:
                # fallback to static data if no frame yet
                frame = [1.5 for _ in range(GRID_SIZE * GRID_SIZE)]


            # draw frame
            clear_screen()
            print("🧭 VisionAssist 8×8 Distance Map (m)\n")
            for r in range(GRID_SIZE):
                row_str = ""
                for c in range(GRID_SIZE):
                    val = frame[r * GRID_SIZE + c]
                    color = get_color(val)
                    if SHOW_VALUES:
                        row_str += f"{color}{val:4.2f}\033[0m "
                    else:
                        row_str += f"{color}██\033[0m "
                print(row_str)
            print("\nPress Ctrl+C to exit visualizer.")
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n🛑 Visual TUI stopped.")


if __name__ == "__main__":
    main()
