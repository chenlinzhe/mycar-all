# """
# Normal camera implementation using remote API.
# """

# import cv2
# import requests

# from src.utils.config_manager import ConfigManager
# from src.utils.logging_config import get_logger

# from .base_camera import BaseCamera

# logger = get_logger(__name__)


# class NormalCamera(BaseCamera):
#     """
#     普通摄像头实现，使用远程API进行分析.
#     """

#     _instance = None

#     def __init__(self):
#         """
#         初始化普通摄像头.
#         """
#         super().__init__()
#         self.explain_url = ""
#         self.explain_token = ""

#     @classmethod
#     def get_instance(cls):
#         """
#         获取单例实例.
#         """
#         if cls._instance is None:
#             with cls._lock:
#                 if cls._instance is None:
#                     cls._instance = cls()
#         return cls._instance

#     def set_explain_url(self, url: str):
#         """
#         设置解释服务的URL.
#         """
#         self.explain_url = url
#         logger.info(f"Vision service URL set to: {url}")

#     def set_explain_token(self, token: str):
#         """
#         设置解释服务的token.
#         """
#         self.explain_token = token
#         if token:
#             logger.info("Vision service token has been set")

#     def capture(self) -> bool:
#         """
#         捕获图像.
#         """
#         try:
#             logger.info("Accessing camera...")

#             # 尝试打开摄像头
#             cap = cv2.VideoCapture(self.camera_index)
#             if not cap.isOpened():
#                 logger.error(f"Cannot open camera at index {self.camera_index}")
#                 return False

#             # 设置摄像头参数
#             cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
#             cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)

#             # 读取图像
#             ret, frame = cap.read()
#             cap.release()

#             if not ret:
#                 logger.error("Failed to capture image")
#                 return False

#             # 获取原始图像尺寸
#             height, width = frame.shape[:2]

#             # 计算缩放比例，使最长边为320
#             max_dim = max(height, width)
#             scale = 320 / max_dim if max_dim > 320 else 1.0

#             # 等比例缩放图像
#             if scale < 1.0:
#                 new_width = int(width * scale)
#                 new_height = int(height * scale)
#                 frame = cv2.resize(
#                     frame, (new_width, new_height), interpolation=cv2.INTER_AREA
#                 )

#             # 直接将图像编码为JPEG字节流
#             success, jpeg_data = cv2.imencode(".jpg", frame)

#             if not success:
#                 logger.error("Failed to encode image to JPEG")
#                 return False

#             # 保存字节数据
#             self.set_jpeg_data(jpeg_data.tobytes())
#             logger.info(
#                 f"Image captured successfully (size: {self.jpeg_data['len']} bytes)"
#             )
#             return True

#         except Exception as e:
#             logger.error(f"Exception during capture: {e}")
#             return False

#     def analyze(self, question: str) -> str:
#         """
#         分析图像.
#         """
#         if not self.explain_url:
#             return '{"success": false, "message": "Image explain URL is not set"}'

#         if not self.jpeg_data["buf"]:
#             return '{"success": false, "message": "Camera buffer is empty"}'

#         # 准备请求头
#         headers = {
#             "Device-Id": ConfigManager.get_instance().get_config(
#                 "SYSTEM_OPTIONS.DEVICE_ID"
#             ),
#             "Client-Id": ConfigManager.get_instance().get_config(
#                 "SYSTEM_OPTIONS.CLIENT_ID"
#             ),
#         }

#         if self.explain_token:
#             headers["Authorization"] = f"Bearer {self.explain_token}"

#         # 准备文件数据
#         files = {
#             "question": (None, question),
#             "file": ("camera.jpg", self.jpeg_data["buf"], "image/jpeg"),
#         }

#         try:
#             # 发送请求
#             response = requests.post(
#                 self.explain_url, headers=headers, files=files, timeout=10
#             )

#             # 检查响应状态
#             if response.status_code != 200:
#                 error_msg = (
#                     f"Failed to upload photo, status code: {response.status_code}"
#                 )
#                 logger.error(error_msg)
#                 return f'{{"success": false, "message": "{error_msg}"}}'

#             # 记录响应
#             logger.info(
#                 f"Explain image size={self.jpeg_data['len']}, "
#                 f"question={question}\n{response.text}"
#             )
#             return response.text

#         except requests.RequestException as e:
#             error_msg = f"Failed to connect to explain URL: {str(e)}"
#             logger.error(error_msg)
#             return f'{{"success": false, "message": "{error_msg}"}}'

"""
Normal camera implementation using remote API.
"""

import os
from datetime import datetime

import cv2
import requests

from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger

from .base_camera import BaseCamera

logger = get_logger(__name__)


class NormalCamera(BaseCamera):
    """
    普通摄像头实现，使用远程API进行分析.
    """

    _instance = None

    def __init__(self):
        """
        初始化普通摄像头.
        """
        super().__init__()
        self.explain_url = ""
        self.explain_token = ""
        
        # 创建img目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.img_dir = os.path.join(current_dir, "img")
        os.makedirs(self.img_dir, exist_ok=True)
        
        print(f">>> NormalCamera初始化完成 (摄像头index={self.camera_index}, 图片目录={self.img_dir})")

    @classmethod
    def get_instance(cls):
        """
        获取单例实例.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def set_explain_url(self, url: str):
        """
        设置解释服务的URL.
        """
        self.explain_url = url
        print(f">>> [重要] Vision service URL 已设置: {url}")
        logger.info(f"Vision service URL set to: {url}")

    def set_explain_token(self, token: str):
        """
        设置解释服务的token.
        """
        self.explain_token = token
        if token:
            print(f">>> [重要] Vision service token 已设置 (长度: {len(token)})")
            logger.info("Vision service token has been set")

    def capture(self) -> bool:
        """
        捕获图像.
        """
        try:
            # 尝试打开摄像头
            cap = cv2.VideoCapture(self.camera_index)
            
            if not cap.isOpened():
                # 自动搜索可用摄像头
                for idx in [0, 1, 2]:
                    test_cap = cv2.VideoCapture(idx)
                    if test_cap.isOpened():
                        ret, test_frame = test_cap.read()
                        if ret:
                            cap = test_cap
                            self.camera_index = idx
                            break
                        else:
                            test_cap.release()
                
                if not cap.isOpened():
                    print(">>> ✗ 未找到可用摄像头")
                    return False

            # 设置参数并读取
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
            ret, frame = cap.read()
            cap.release()

            if not ret:
                print(">>> ✗ 无法读取图像")
                return False
            
            # 保存原始图像
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_path = os.path.join(self.img_dir, f"photo_{timestamp}_original.jpg")
            cv2.imwrite(original_path, frame)
            print(f">>> ✓ 拍照成功，已保存: {original_path}")

            # 缩放图像
            height, width = frame.shape[:2]
            max_dim = max(height, width)
            scale = 320 / max_dim if max_dim > 320 else 1.0

            if scale < 1.0:
                new_width = int(width * scale)
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

            # 编码为JPEG
            success, jpeg_data = cv2.imencode(".jpg", frame)
            if not success:
                print(">>> ✗ JPEG编码失败")
                return False

            # 保存数据
            jpeg_bytes = jpeg_data.tobytes()
            self.set_jpeg_data(jpeg_bytes)
            
            # 保存缩放后的图像
            resized_path = os.path.join(self.img_dir, f"photo_{timestamp}_resized.jpg")
            with open(resized_path, 'wb') as f:
                f.write(jpeg_bytes)
            
            return True

        except Exception as e:
            print(f">>> ✗ 拍照异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def analyze(self, question: str) -> str:
        """
        分析图像 - 详细调试版本.
        """
        print("\n" + "=" * 70)
        print(">>> [分析开始] 图像分析流程启动")
        print("=" * 70)
        print(f">>> 问题: {question}")
        
        # 检查URL
        print(f"\n>>> [检查1] explain_url 值: '{self.explain_url}'")
        print(f">>> [检查1] explain_url 类型: {type(self.explain_url)}")
        print(f">>> [检查1] explain_url 是否为空: {not self.explain_url}")
        print(f">>> [检查1] explain_url 长度: {len(self.explain_url) if self.explain_url else 0}")
        
        if not self.explain_url:
            error = "图像解释URL未设置"
            print(f">>> ✗ [错误] {error}")
            print("=" * 70 + "\n")
            return '{"success": false, "message": "Image explain URL is not set"}'

        # 检查缓冲区
        print(f"\n>>> [检查2] jpeg_data buffer 大小: {self.jpeg_data['len']} 字节")
        print(f">>> [检查2] jpeg_data buffer 是否为空: {not self.jpeg_data['buf']}")
        
        if not self.jpeg_data["buf"]:
            error = "摄像头缓冲区为空"
            print(f">>> ✗ [错误] {error}")
            print("=" * 70 + "\n")
            return '{"success": false, "message": "Camera buffer is empty"}'

        # 解析URL
        print(f"\n>>> [URL详情]")
        print(f">>> 完整URL: {self.explain_url}")
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.explain_url)
            print(f">>> 协议(scheme): {parsed.scheme}")
            print(f">>> 主机(hostname): {parsed.hostname}")
            print(f">>> 端口(port): {parsed.port if parsed.port else '默认'}")
            print(f">>> 路径(path): {parsed.path}")
            print(f">>> 查询参数(query): {parsed.query if parsed.query else '无'}")
        except Exception as e:
            print(f">>> URL解析异常: {e}")

        # 准备请求头
        print(f"\n>>> [请求头]")
        device_id = ConfigManager.get_instance().get_config("SYSTEM_OPTIONS.DEVICE_ID")
        client_id = ConfigManager.get_instance().get_config("SYSTEM_OPTIONS.CLIENT_ID")
        
        print(f">>> Device-Id: {device_id}")
        print(f">>> Client-Id: {client_id}")
        
        headers = {
            "Device-Id": device_id,
            "Client-Id": client_id,
        }

        if self.explain_token:
            token_preview = self.explain_token[:20] + "..." if len(self.explain_token) > 20 else self.explain_token
            headers["Authorization"] = f"Bearer {self.explain_token}"
            print(f">>> Authorization: Bearer {token_preview} (总长度: {len(self.explain_token)})")
        else:
            print(">>> Authorization: 未设置")

        # 准备上传数据
        print(f"\n>>> [上传数据]")
        print(f">>> question参数: {question}")
        print(f">>> file名称: camera.jpg")
        print(f">>> file大小: {len(self.jpeg_data['buf'])} 字节")
        print(f">>> file类型: image/jpeg")
        
        files = {
            "question": (None, question),
            "file": ("camera.jpg", self.jpeg_data["buf"], "image/jpeg"),
        }

        # 发送请求
        print(f"\n>>> [发送请求]")
        print(f">>> 目标URL: {self.explain_url}")
        print(f">>> 方法: POST")
        print(f">>> 超时: 10秒")
        print(f">>> 正在连接...")
        
        try:
            response = requests.post(
                self.explain_url, 
                headers=headers, 
                files=files, 
                timeout=10
            )

            print(f"\n>>> [响应]")
            print(f">>> 状态码: {response.status_code}")
            print(f">>> 响应头: {dict(response.headers)}")
            print(f">>> 响应内容长度: {len(response.text)} 字符")
            print(f">>> 响应内容: {response.text[:500]}...")  # 只显示前500字符

            if response.status_code != 200:
                print(f">>> ✗ [失败] HTTP状态码非200")
                print("=" * 70 + "\n")
                return f'{{"success": false, "message": "HTTP {response.status_code}"}}'

            print(f">>> ✓ [成功] 图像分析完成")
            print("=" * 70 + "\n")
            return response.text

        except requests.Timeout as e:
            print(f"\n>>> ✗ [超时] 请求超时(10秒): {str(e)}")
            print("=" * 70 + "\n")
            return '{"success": false, "message": "Request timeout"}'
            
        except requests.ConnectionError as e:
            print(f"\n>>> ✗ [连接错误] 无法连接到服务器:")
            print(f">>> 错误详情: {str(e)}")
            print(f">>> 可能原因:")
            print(f">>>   1. 服务器 {self.explain_url} 未启动")
            print(f">>>   2. 网络不通")
            print(f">>>   3. 防火墙阻止")
            print(f">>>   4. URL配置错误")
            print("=" * 70 + "\n")
            return '{"success": false, "message": "Connection error"}'
            
        except Exception as e:
            print(f"\n>>> ✗ [异常] 未知错误: {str(e)}")
            import traceback
            print(">>> 堆栈跟踪:")
            traceback.print_exc()
            print("=" * 70 + "\n")
            return '{"success": false, "message": "Unknown error"}'