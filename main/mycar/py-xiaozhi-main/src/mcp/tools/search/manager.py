"""搜索工具管理器.  
  
负责搜索工具的初始化、配置和MCP工具注册  
"""  
  
from typing import Any, Dict  
from src.utils.logging_config import get_logger  
from .tools import search_item  
  
logger = get_logger(__name__)  
  
class SearchManager:  
    """  
    搜索工具管理器.  
    """  
  
    def __init__(self):  
        """  
        初始化搜索工具管理器.  
        """  
        self._initialized = False  
        logger.info("[SearchManager] 搜索工具管理器初始化")  


    def set_vision_config(self, url: str, token: str):  
        """设置视觉服务配置"""  
        self._vision_url = url  
        self._vision_token = token  
        logger.info(f"Search manager vision config: {url}")

        
    def init_tools(self, add_tool, PropertyList, Property, PropertyType):  
        """初始化并注册搜索工具"""  
        from .tools import search_item, get_search_status, cancel_search  
        
        # 1. 启动搜索任务  
        search_props = PropertyList([  
            Property("target_item", PropertyType.STRING)  
        ])  
        add_tool((  
            "self.search.start",  
            "启动物品搜索任务,机器人将移动并使用摄像头寻找指定物品。"  
            "立即返回任务ID,可通过 self.search.get_status 查询进度。\n"  
            "使用场景:\n"  
            "1. 用户要求寻找某个物品\n"  
            "2. 需要机器人视觉搜索功能\n"  
            "参数:\n"  
            "- target_item: 要搜索的物品名称(如'电脑','杯子','手机')",  
            search_props,  
            search_item  
        ))  
        
        # 2. 查询搜索状态  
        status_props = PropertyList([  
            Property("task_id", PropertyType.STRING)  
        ])  
        add_tool((  
            "self.search.get_status",  
            "查询搜索任务的当前状态和进度。\n"  
            "返回信息包括:\n"  
            "- status: running(运行中)/found(找到)/not_found(未找到)/error(错误)/cancelled(已取消)\n"  
            "- progress: 进度百分比(0-100)\n"  
            "- result: 搜索结果描述\n"  
            "- elapsed_seconds: 已运行时间\n"  
            "参数:\n"  
            "- task_id: 启动搜索时返回的任务ID",  
            status_props,  
            get_search_status  
        ))  
        
        # 3. 取消搜索任务  
        cancel_props = PropertyList([  
            Property("task_id", PropertyType.STRING)  
        ])  
        add_tool((  
            "self.search.cancel",  
            "取消正在运行的搜索任务,停止机器人运动。\n"  
            "使用场景:\n"  
            "1. 用户要求停止搜索\n"  
            "2. 搜索时间过长需要中断\n"  
            "参数:\n"  
            "- task_id: 要取消的任务ID",  
            cancel_props,  
            cancel_search  
        ))  
        
        logger.info("[SearchManager] 搜索工具注册完成(异步模式)")
  
    def is_initialized(self) -> bool:  
        """检查管理器是否已初始化."""  
        return self._initialized  
  
# 全局管理器实例  
_search_manager = None  
  
def get_search_manager() -> SearchManager:  
    """获取搜索工具管理器单例."""  
    global _search_manager  
    if _search_manager is None:  
        _search_manager = SearchManager()  
        logger.debug("[SearchManager] 创建搜索工具管理器实例")  
    return _search_manager