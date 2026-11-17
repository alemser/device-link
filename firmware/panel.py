"""Presses the KX-393's STANDBY/ON key, which has no remote code, on the KEY1 line.

The service manual's schematic: STANDBY/ON (SW1, on its own small board) shorts KEY1 straight to ground. KEY1 is an
analogue input of the microcontroller (IC12 pin 1), pulled to +5 V through 10 kΩ (R142), and shared with STOP, PLAY,
FF, REW and the intro keys, each through a resistor ladder. KEY1 runs on the 27-way flat between the main board (CB7)
and the front board (CB8). Pressing = KEY1 at 0 V for a moment.

Wiring (planned): GP7 on the KEY1 joint of CB8. Same rule as the IR line: GP7 is never driven to 1; its output stays
0 and only the direction changes. Released, the line sits at about 4.8 V through R142: the RP2350's pins tolerate it
while the Pico is powered, and the Pico takes its power from the same deck.

press() runs on the Pico only; PRESS_MS is checked by tools/test_control.py.
"""

import asyncio

from machine import Pin

KEY1_PIN = 7
PRESS_MS = 200                  # long enough for the microcontroller's key scan; to confirm on the deck


class Panel:
    def __init__(self):
        self.key1 = Pin(KEY1_PIN, Pin.IN, pull=None)
        self.key1.value(0)      # the output value stays 0; only the direction changes
        self.pressing = False
        self.presses = 0

    async def press_power(self):
        self.pressing = True
        try:
            self.key1.init(Pin.OUT, value=0)
            await asyncio.sleep_ms(PRESS_MS)
        finally:
            self.key1.init(Pin.IN, pull=None)
            self.pressing = False
        self.presses += 1
