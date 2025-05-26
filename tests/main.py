# tests/test.py
import asyncio

from . import CONFIG, TestTree


async def main():
    test_tree = TestTree.build()
    await test_tree.execute()


# 运行测试: `python -m tests.main`
if __name__ == "__main__":
    # TODO: 全局配置
    CONFIG["BASE_URL"] = "http://localhost:8004"

    # TODO: 测试文件需要在这里引入
    from .test_example import *  # noqa: F403

    asyncio.run(main())
