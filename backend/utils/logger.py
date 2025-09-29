import sys
from typing import Any

from loguru import logger

# 保存当前模块名，用于日志上下文
_name = __name__

logger.remove()

# 使用 {name} 格式，并打补丁设置模块名
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {name}:{line} | {level} | {message}",
    level="INFO",
)


# ✅ 让 logger 记住当前模块名
def module_patcher(record: dict[str, Any]) -> None:
    record["name"] = _name


logger = logger.patch(module_patcher)  # type: ignore[arg-type]

# 明确导出 logger 属性
__all__ = ["logger"]

# 现在导入这个 logger 的地方，日志都会带上模块名
# from backend.utils.logger import logger
# logger.info("This is an info message")
