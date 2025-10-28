"""
serial_listener.py
------------------
Reads ESP32 sensor data from Serial (LIVE mode) or from a saved log file (TEST mode).

Format expected:
    SENSOR|TIMESTAMP|[v1,v2,v3,...]

Examples:
    TOF|2025-10-12 21:03:11|[0.6,0.7,0.8,...]
    US|2025-10-12 21:03:11|[87.3]
"""

import serial
import time
import sys
from datetime import datetime
from pathlib import Path
import re

# === CONFIGURATION ===
MODE = "TEST"                  # "LIVE" or "TEST"
PORT = "COM5"                  # e.g. "COM5" on Windows or "/dev/ttyUSB0" on Linux
BAUD = 115200
TIMEOUT = 2
TEST_FILE = Path("fake_sensor_log.txt")
SPEED = 0.2                    # seconds between lines in test mode


# === PARSER ===
def parse_sensor_line(line: str):
    """Parse lines like TOF|2025-10-12 09:23:53|[0.7,0.6,...]"""
    # Remove extra whitespace and carriage returns
    line = line.strip().replace('\r', '').replace('\n', '')
    
    # NEW FIX: Remove null characters that cause float conversion errors
    line = line.replace('\x00', '')
    
    if not line or "|" not in line:
        return None

    try:
        # Split into three parts: SENSOR, TIMESTAMP, VALUES
        sensor_type, timestamp_str, values_str = line.split("|", 2)
        
        # Strip whitespace from values_str before the regex
        values_str = values_str.strip() 
        
        # Use a simple regex to extract content inside brackets
        values_match = re.search(r"\[(.+)\]", values_str)
        
        if not values_match:
            print(f"[ERROR] Malformed value list: {values_str}")
            return None
        
        # The content inside the brackets (e.g., "0.7,0.6,..." or "92.3")
        values_list_content = values_match.group(1).strip()

        # Convert the comma-separated string of values to a list of floats
        values = [float(v.strip()) for v in values_list_content.split(',') if v.strip()]
        
        # Convert the timestamp string to a datetime object
        timestamp = datetime.strptime(timestamp_str.strip(), "%Y-%m-%d %H:%M:%S")

        return {
            "type": sensor_type.strip(),
            "timestamp": timestamp,
            "values": values
        }

    except ValueError as e:
        # This catches errors from split, strptime, or float conversion
        print(f"[ERROR] Parsing failed for line '{line[:60]}...': {e}")
        return None
    except Exception as e:
        # Catch any unexpected errors
        print(f"[FATAL] An unexpected error occurred: {e}")
        return None


# === DISPLAY ===
def display(entry: dict):
    """Prints the parsed sensor data. MODIFIED to return full values list."""
    timestamp = entry['timestamp'].strftime("%H:%M:%S")
    sensor_type = entry['type']
    values = entry['values']
    
    if sensor_type == "TOF":
        # MODIFIED: Print the entire list of values in the requested format
        values_str = ",".join([f"{v:.1f}" for v in values])
        print(f"[{timestamp}] TOF: [{values_str}]")
    elif sensor_type == "US":
        distance = values[0] if values else -1.0
        print(f"[{timestamp}] US : Distance={distance:.1f}cm")
    else:
        print(f"[{timestamp}] UNKNOWN SENSOR: {sensor_type}")


# === MAIN FUNCTIONS ===
def run_live():
    """Connect to the serial port and read data in real-time."""
    try:
        ser = serial.Serial(PORT, BAUD, timeout=TIMEOUT)
        print(f"[{datetime.now()}] LIVE mode on {PORT} @ {BAUD} baud\n")
    except serial.SerialException as e:
        print(f"❌ Could not open port: {e}")
        sys.exit(1)

    try:
        while True:
            # Read a line from the serial port, decode it, and clean up
            raw = ser.readline().decode(errors="ignore").strip()
            if not raw:
                continue
            
            entry = parse_sensor_line(raw)
            if entry:
                display(entry)
    except KeyboardInterrupt:
        print("\nExiting live mode.")
    finally:
        ser.close()


def run_test():
    """Replay data from a saved file."""
    if not TEST_FILE.exists():
        print(f"❌ Test file not found: {TEST_FILE}")
        sys.exit(1)

    print(f"[{datetime.now()}] TEST mode replay from {TEST_FILE}\n")

    with open(TEST_FILE, "r", encoding="utf-8-sig", errors="ignore") as f:

        for raw in f:
            raw = raw.strip()  # Remove newline + spaces
            
            # 1. Skip truly blank lines
            if not raw:
                continue

            # 2. Filter out non-data/comment lines (headers, etc.)
            if "|" not in raw:
                continue
                
            entry = parse_sensor_line(raw)
            if entry:
                display(entry)
            else:
                # This should now only trigger if the line structure is fundamentally broken
                print(f"[WARN] Malformed: {raw}")
            
            time.sleep(SPEED) # Throttle the output for readability


# === EXECUTION ===
if __name__ == "__main__":
    if MODE == "LIVE":
        run_live()
    elif MODE == "TEST":
        run_test()
    else:
        print(f"❌ Invalid MODE setting: {MODE}. Must be 'LIVE' or 'TEST'.")