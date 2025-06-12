import asyncio

async def power_sim(a, b, delay_seconds=5):
    """Simulate a power operation that sleeps for `delay_seconds` between iterations."""

    result = a
    for _ in range(1, b):
        result *= a
        print("Computing...", result)
        await asyncio.sleep(delay_seconds)
    return result

async def failing_sim(a, delay_seconds=5):
    """Simulate an operation that will raise an exception after sleeping `a` times for `delay_seconds`."""

    for _ in range(0, a):
        print("Computing...")
        await asyncio.sleep(delay_seconds)
    raise ValueError("Simulated failure in failing_sim")