"""
event_bus.py — shared event queue between controller and sensor modules
"""

import queue

EVENT_QUEUE = queue.Queue()
VISION_QUEUE = queue.Queue()

