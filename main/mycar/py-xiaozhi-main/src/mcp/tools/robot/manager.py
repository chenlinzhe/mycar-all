# ================================================
# 必须放在文件最最顶部 ─ 任何 import 之前
# ================================================

import sys
from pathlib import Path

# 计算项目根目录（mycar）
# 当前文件在：py-xiaozhi-main/src/mcp/tools/robot/manager.py
# 向上跳 5 层 → mycar
script_path = Path(__file__).resolve()
project_root = script_path.parents[5]   # parents[5] 对应 /home/pi/mycar

clbrobot_dir = project_root / "CLBROBOT"
clbrobot_str = str(clbrobot_dir.resolve())

# 添加到 sys.path 最前面（优先查找）
if clbrobot_str not in sys.path:
    sys.path.insert(0, clbrobot_str)

# ────────────────────────────────────────────────
# 调试打印（运行一次后可注释掉）
print("[DEBUG] 添加的 CLBROBOT 路径:", clbrobot_str)
print("[DEBUG] 该路径是否存在？", clbrobot_dir.exists())
print("[DEBUG] LOBOROBOT.py 是否存在？", (clbrobot_dir / "LOBOROBOT.py").exists())
print("[DEBUG] sys.path 前4项（应包含 CLBROBOT）：")
for p in sys.path[:4]:
    print("  ", p)
# ────────────────────────────────────────────────

# 现在安全导入
try:
    from LOBOROBOT import LOBOROBOT
    print("[SUCCESS] LOBOROBOT 导入成功")
except ImportError as e:
    print("[IMPORT ERROR]", str(e))
    print("如果还是失败，请检查：")
    print("1. 文件名是否严格为 LOBOROBOT.py（大小写敏感）")
    print("2. LOBOROBOT.py 文件是否有语法错误？（运行 python /home/pi/mycar/CLBROBOT/LOBOROBOT.py 测试）")
    LOBOROBOT = None

# ================================================
# 下面才是你原来的 import 和代码
# ================================================

import re
from typing import Any, Dict

# logger 需要在这一行之前定义，或者移到这里
from src.utils.logging_config import get_logger
logger = get_logger(__name__)




class RobotManager:
    def __init__(self):
        self._robot = None
        self._init_robot()

    def _init_robot(self):
        """延迟初始化机器人实例"""
        if self._robot is not None:
            return

        if LOBOROBOT is None:
            logger.error("LOBOROBOT 库不可用，无法初始化机器人")
            return

        try:
            # 根据你的实际库修改初始化方式
            self._robot = LOBOROBOT()           # 可能需要端口、IP、串口等参数
            logger.info("机器人初始化成功")
        except Exception as e:
            logger.error("机器人初始化失败", exc_info=True)
            self._robot = None
            raise RuntimeError(f"机器人初始化失败: {e}")

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        """注册统一的机器人控制工具"""
        props = PropertyList([
            Property("action", PropertyType.STRING),
            Property("quantity", PropertyType.STRING),
            # 如果这个框架要求所有参数都有默认值，也可以写成：
            # Property("quantity", PropertyType.STRING, default_value=""),
        ])

        add_tool((  
            "robot_control",  

            # 这里把详细描述全部写进工具的说明字符串里（这是最可靠的方式）
            """智能机器人控制工具。支持自然语言风格指令控制机器人移动。

    使用场景：用户要求机器人前进、转向、停止等操作。

    参数说明：
    - action（字符串，必填）：机器人动作类型，支持以下值：
    '前进'、'后退'、'左转'、'右转'、'左移'、'右移'、'停止'
    - quantity（字符串，可选）：动作的量或修饰词，例如：
    - '两步'、'3秒'、'90度'
    - '快速'、'慢速'、'快'、'慢'
    - 组合如 '快速5秒'、'慢速两步'

    解析规则示例：
    '向前走两步'     → action='前进', quantity='两步'
    '左转90度'        → action='左转', quantity='90度'
    '快速后退5秒'     → action='后退', quantity='快速5秒'
    '停车'            → action='停止', quantity=''
    '慢速前进'        → action='前进', quantity='慢速'

    速度映射（从 quantity 中识别）：
    - 包含 '快速'/'快'/'高速' → 速度 80
    - 包含 '慢速'/'慢'/'低速' → 速度 30
    - 其他情况（包括无速度描述） → 速度 50

    持续时间/距离映射（从 quantity 中解析）：
    - 匹配数字 + '步'/'秒'/'度' → 提取数字
    - 单位为 '度' 时转换为时间（当前系数：1度 ≈ 0.0167秒，可根据实际标定调整）
    - 无明确数字/单位时默认 1 秒""",
            props,  
            self.robot_control  
        ))


    async def robot_control(self, args: Dict[str, Any]) -> str:
        """统一的机器人控制函数"""
        try:
            self._init_robot()
            if self._robot is None:
                return "机器人未初始化，无法执行动作"

            action = args.get("action", "").strip()
            quantity = args.get("quantity", "").strip()

            if not action:
                return "缺少动作类型（action）"

            speed = self._parse_speed(quantity)
            duration = self._parse_duration(quantity)

            result = await self._execute_action(action, speed, duration)

            logger.info(
                f"[Robot] action={action} quantity={quantity!r} → "
                f"speed={speed} duration={duration}s → {result}"
            )
            return result

        except Exception as e:
            logger.error(f"[Robot] 控制失败: {e}", exc_info=True)
            return f"机器人控制失败：{str(e)}"

    def _parse_speed(self, quantity: str) -> int:
        """从 quantity 中提取速度描述"""
        q = quantity.lower()
        if any(word in q for word in ["快速", "快", "高速"]):
            return 80
        if any(word in q for word in ["慢速", "慢", "低速"]):
            return 30
        return 50  # 默认中速

    def _parse_duration(self, quantity: str) -> float:  
        """解析持续时间/步数/角度 → 统一转为秒"""  
        # 中文数字映射  
        chinese_numbers = {  
            '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5,  
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10  
        }  
        
        # 先尝试匹配阿拉伯数字  
        match = re.search(r'(\d+\.?\d*)\s*(步|秒|度)?', quantity)  
        if match:  
            number = float(match.group(1))  
            unit = match.group(2) or "秒"  
        else:  
            # 尝试匹配中文数字  
            for cn_num, num in chinese_numbers.items():  
                if cn_num in quantity:  
                    match = re.search(r'(步|秒|度)?', quantity[quantity.index(cn_num)+1:])  
                    unit = match.group(1) if match else "秒"  
                    number = float(num)  
                    break  
            else:  
                return 1.0  # 默认1秒  
        
        # 单位转换逻辑保持不变  
        if unit == "步":  
            return number  
        elif unit == "秒":  
            return number  
        elif unit == "度":  
            return number / 60.0  
        return 1.0

    async def _execute_action(self, action: str, speed: int, duration: float) -> str:  
        """实际执行机器人动作"""  
        if self._robot is None:  
            return "机器人对象不可用"  

        # 打印调试信息  
        print(f"执行动作: {action}, 速度: {speed}, 持续时间: {duration}秒")  
    
        action_map = {  
            "前进": ("前进", lambda s, d: self._robot.t_up(s, d)),  
            "后退": ("后退", lambda s, d: self._robot.t_down(s, d)),  
            "左转": ("左转", lambda s, d: self._robot.turnLeft(s, d)),  
            "右转": ("右转", lambda s, d: self._robot.turnRight(s, d)),  
            "左移": ("左移", lambda s, d: self._robot.moveLeft(s, d)),  
            "右移": ("右移", lambda s, d: self._robot.moveRight(s, d)),  
            "停止": ("停止", lambda s, d: self._robot.t_stop(d))  
        }  
    
        if action not in action_map:  
            return f"不支持的动作：{action}"  
    
        action_name, action_func = action_map[action]  
    
        try:  
            if action == "停止":  
                action_func(0, 0)  
                return "机器人已停止"  
            else:  
                action_func(speed, duration)  
                return f"机器人正在{action_name}，速度 {speed}，持续约 {duration:.1f} 秒"  
        except Exception as e:  
            logger.error(f"执行 {action_name} 失败", exc_info=True)  
            return f"{action_name} 执行失败：{str(e)}"
# 全局单例（简单实现，生产环境建议用依赖注入）
_manager = None


def get_robot_manager():
    """获取机器人管理器单例"""
    global _manager
    if _manager is None:
        _manager = RobotManager()
    return _manager