from collections.abc import Callable, Coroutine
from typing import Any

from .task_group import TaskGroup


async def async_sort(
    data: list,
    key: Callable[[Any], Coroutine],
    reverse: bool = False,
) -> list:
    """
    异步版本快速排序

    Args:
        data (list): 待排序列表
        key (Callable[[Any], Coroutine]): 异步获取data中元素的值
        reverse (bool): 默认为 False, 从小到大排

    example key func:
    ```python
        async def key(x):
            return await get_name(x)
    ```

    Returns:
        list: 返回排序好的列表

    """
    task_group = TaskGroup()
    for item in data:
        task_group.append(key(item))
    value = await task_group.get()

    def cmp(x, y):
        if reverse:
            return x > y
        return x < y

    async def quick_sort(left: int, right: int):
        nonlocal key
        nonlocal data
        nonlocal value

        if left >= right:
            return

        # 使data左边都小于mid_value, 右边都大于mid_value
        idx = (left + right) // 2
        mid_value = value[idx]
        i_left = left - 1
        i_right = right + 1
        while i_left < i_right:
            i_left += 1
            while cmp(value[i_left], mid_value):
                i_left += 1

            i_right -= 1
            while cmp(mid_value, value[i_right]):
                i_right -= 1

            if i_left < i_right:
                data[i_left], data[i_right] = data[i_right], data[i_left]
                value[i_left], value[i_right] = value[i_right], value[i_left]

        # 递归处理左右两边的子区间
        await quick_sort(left, i_right)
        await quick_sort(i_right + 1, right)

    # quick_sort() end

    await quick_sort(0, len(data) - 1)
    return data
