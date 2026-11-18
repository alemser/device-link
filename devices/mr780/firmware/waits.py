"""Waiting for something to happen, without stopping the rest of the bridge.

This file belongs to the shared base (firmware-base/): change it there and copy it with copy_base.py --all, never here.

    await until(lambda: not remote.sending(), 2000)     # True as soon as it holds, False if ms ran out

Runs the same in MicroPython (Pico) and in the computer's Python (the devices' tools/test_*.py). On the Pico it sleeps
with asyncio.sleep_ms; a test may replace that to make waits instant.
"""

import asyncio


async def until(ready, ms, step_ms=10):
    """Checks ready() every step_ms for up to ms. True once it holds; False if it never did."""
    for _ in range(ms // step_ms):
        if ready():
            return True
        sleep_ms = getattr(asyncio, "sleep_ms", None)      # MicroPython's; CPython has only sleep()
        await (sleep_ms(step_ms) if sleep_ms else asyncio.sleep(step_ms / 1000))
    return ready()
