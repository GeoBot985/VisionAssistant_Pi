"""
fusion_runner.py — bridges serial_listener (TEST mode) with sensor_processor.
Use this to simulate sensor fusion and audio feedback before real hardware.
"""

from serial_listener import parse_sensor_line
from sensor_processor import process_entry
from datetime import datetime
from pathlib import Path
import time

# Path to the simulated log file
LOG_FILE = Path("fake_sensor_log.txt")

def main():
    if not LOG_FILE.exists():
        print(f"❌ Log file not found: {LOG_FILE}")
        return

    print(f"🧪 Running simulation from {LOG_FILE}...\n")

    with open(LOG_FILE, "r", encoding="utf-8-sig", errors="ignore") as f:
        for raw in f:
            raw = raw.strip()
            if not raw or "|" not in raw:
                continue

            entry = parse_sensor_line(raw)
            if entry:
                process_entry(entry)
            else:
                print(f"[WARN] Skipped malformed line: {raw[:60]}...")

            # Throttle slightly for readability
            time.sleep(0.1)

    print("\n✅ Simulation complete.")


if __name__ == "__main__":
    main()
