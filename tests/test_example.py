from . import test_task


@test_task("tag1")
def test_a():
    print("test_a")


@test_task("tag2", dependencies=[test_a])
async def test_b():
    import asyncio

    await asyncio.sleep(1)
    print("test_b")


@test_task("tag3", dependencies=[test_a])
async def test_c():
    import asyncio

    await asyncio.sleep(1)
    print("test_c")


@test_task("tag4", dependencies=[test_b, test_c])
async def test_d():
    import asyncio

    await asyncio.sleep(1)
    print("test_d")
