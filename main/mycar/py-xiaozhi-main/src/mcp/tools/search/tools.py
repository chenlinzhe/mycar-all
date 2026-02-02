try:      
    from LOBOROBOT import LOBOROBOT      
    print("[SUCCESS] LOBOROBOT 导入成功")      
except ImportError as e:      
    print("[IMPORT ERROR]", str(e))      
    LOBOROBOT = None      
      
# ================================================      
# 导入日志系统      
# ================================================      
from src.utils.logging_config import get_logger    
logger = get_logger(__name__)    
    
# 其他导入    
import time        
import json        
import threading        
import cv2    
from concurrent.futures import ThreadPoolExecutor        
from src.utils.logging_config import get_logger  
  
import os    
import datetime    
import requests    
from src.utils.config_manager import ConfigManager   
from src.mcp.tools.camera import get_camera_instance

import uuid  
  
# 全局任务管理器 - 添加在 ConcurrentSearcher 类定义之前  
_active_searches = {}  
_search_lock = threading.Lock()


    
class ConcurrentSearcher:    
    """并发搜索器 - 高分辨率显示和远程分析"""    
            
    def __init__(self, camera, clbrobot, target_item, progress_callback=None, task_state=None):  
        self.camera = camera  
        self.clbrobot = clbrobot  
        self.target_item = target_item  
        self.found = False  
        self.search_active = True  
        self.lock = threading.Lock()  
        self.result_message = ""  
        
        # 初始化配置相关属性  
        self.explain_url = ""  
        self.explain_token = ""  
        self.device_id = ""  
        self.client_id = ""  
        
        # 新增: 进度回调和任务状态  
        self.progress_callback = progress_callback  
        self.task_state = task_state  

            
        # 创建img目录    
        self.img_dir = os.path.join(os.path.dirname(__file__), "img")    
        if not os.path.exists(self.img_dir):    
            os.makedirs(self.img_dir)    
            logger.info(f"创建图片保存目录: {self.img_dir}")    
            
        # 持续打开摄像头 - 高分辨率    
        self.cap = cv2.VideoCapture(0)    
        if not self.cap.isOpened():    
            logger.error("无法打开摄像头")    
            raise RuntimeError("摄像头初始化失败")    
                
        # 设置高分辨率用于显示    
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)    
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)    
        logger.info("摄像头已持续打开，分辨率设置为640x480")    

        # 在实例化时获取并设置VLLM地址  
        self._setup_vision_service()


    def _setup_vision_service(self):  
        """在实例化时设置视觉服务地址"""  
        try:  
            # 优先尝试从搜索管理器获取MCP配置  
            from .manager import get_search_manager  
            search_manager = get_search_manager()  

            config = ConfigManager.get_instance()  
            
            if hasattr(search_manager, '_vision_url') and search_manager._vision_url:  
                self.explain_url = search_manager._vision_url  
                self.explain_token = getattr(search_manager, '_vision_token', '')  
                print(f"[配置成功] 使用MCP动态配置的地址: {self.explain_url}")  
            else:  
                # 降级到本地配置  

                explain_url = config.get_config("CAMERA.Local_VL_url")  
                explain_token = config.get_config("CAMERA.VLapi_key")  
                
                self.explain_url = explain_url or "http://1.12.222.251:8003/mcp/vision/explain"  
                self.explain_token = explain_token  
                print(f"[配置降级] 使用本地配置的地址: {self.explain_url}")  
            
            # 获取认证信息  
            self.device_id = config.get_config("SYSTEM_OPTIONS.DEVICE_ID")  
            self.client_id = config.get_config("SYSTEM_OPTIONS.CLIENT_ID")  
            
        except Exception as e:  
            self.explain_url = "http://1.12.222.251:8003/mcp/vision/explain"  
            self.device_id = ""  
            self.client_id = ""  
            print(f"[配置错误] 获取配置失败: {e}，使用默认地址: {self.explain_url}")

    # 在这里添加 _call_mcp_vision_tool 方法  
    async def _call_mcp_vision_tool(self, frame):  
        """使用已捕获的帧进行MCP分析"""  
        try:  
            # 将frame转换为JPEG并设置到摄像头实例  
            success, jpeg_data = cv2.imencode(".jpg", frame)  
            if success:  
                camera = get_camera_instance()  
                camera.set_jpeg_data(jpeg_data.tobytes())  
                
                # 直接调用分析而不重新拍照  
                result = camera.analyze(f"图中是否有{self.target_item}？...")  
                return result  
        except Exception as e:  
            logger.error(f"MCP视觉工具调用失败: {e}")  
            return None


        
    def _save_frame_to_file(self, frame, suffix=""):    
        """保存帧到本地文件"""    
        try:    
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")    
            filename = f"search_{timestamp}{suffix}.jpg"    
            filepath = os.path.join(self.img_dir, filename)    
            cv2.imwrite(filepath, frame)    
            logger.info(f"图片已保存: {filepath}")    
            return filepath    
        except Exception as e:    
            logger.error(f"保存图片失败: {e}")    
            return None    



    def _send_frame_to_analysis(self, frame):  
        """发送帧到远程AI分析服务"""  
        try:  
            if not self.explain_url:  
                logger.error("VLLM服务地址未配置")  
                return None  
                
            # 准备高分辨率图像用于分析  
            analysis_frame = frame.copy()  
            height, width = analysis_frame.shape[:2]  
            max_dim = max(height, width)  
            scale = 640 / max_dim if max_dim > 640 else 1.0  
            
            if scale < 1.0:  
                new_width = int(width * scale)  
                new_height = int(height * scale)  
                analysis_frame = cv2.resize(analysis_frame, (new_width, new_height), interpolation=cv2.INTER_AREA)  
            
            # 编码为JPEG  
            success, jpeg_data = cv2.imencode(".jpg", analysis_frame)  
            if not success:  
                return None  
            
            jpeg_bytes = jpeg_data.tobytes()  
            
            # 保存图片到本地  
            self._save_frame_to_file(frame)  
            
            # 生成动态文件名  
            import datetime  
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  
            dynamic_filename = f"search_{timestamp}.jpg"  
            
            # 准备请求头 - 不要手动设置Content-Type  
            headers = {  
                "Device-Id": self.device_id,  
                "Client-Id": self.client_id  
            }  
            
            # print(f"[认证信息] Device-Id: {self.device_id}")  
            # print(f"[认证信息] Client-Id: {self.client_id}")  
            
            # 添加Authorization token  
            if self.explain_token:  
                headers["Authorization"] = f"Bearer {self.explain_token}"  
                # print(f"[认证信息] 使用Bearer token认证")  
            
            # 使用动态文件名的multipart数据  
            files = {  
                "question": (None, f"图中是否有{self.target_item}？如果有，请回答'找到了'并描述其位置。如果没有，请回答'没有'。"),  
                "file": (dynamic_filename, jpeg_bytes, "image/jpeg")  # 使用动态文件名  
            }  
            
            # print(f"[远程识别] 发送请求到服务器: {self.explain_url}")  
            # print(f"[远程识别] 图片大小: {len(jpeg_bytes)} 字节")  
            print(f"[远程识别] 使用文件名: {dynamic_filename}")  

                    # 记录开始时间  
            start_time = time.time()  
            print(f"[VLLM计时] 开始发送请求到: {self.explain_url}")  
            
            # 发送请求 - requests会自动设置正确的Content-Type和boundary  
            response = requests.post(self.explain_url, headers=headers, files=files, timeout=10)  

            # 记录结束时间并计算耗时  
            end_time = time.time()  
            duration = end_time - start_time  
            print(f"[VLLM计时] 请求完成，耗时: {duration:.2f}秒")  


            if response.status_code == 200:  
                print(f"\n[识别结果] 服务器返回: {response.text}")  
                logger.info(f"识别结果: {response.text}")  
                return response.text  
            else:  
                print(f"[错误] 服务器返回状态码: {response.status_code}")  
                return None  
                
        except Exception as e:  
            print(f"[错误] 远程识别失败: {e}")  
            logger.error(f"远程识别失败: {e}")  
            return None
                

                

  
    def _parse_result(self, result):  
        """解析AI分析结果"""  
        try:  
            import json  
            data = json.loads(result)  
            if data.get("success"):  
                response = data.get("response", "")  
                return response  
            return None  
        except Exception as e:  
            logger.error(f"解析结果失败: {e}")  
            return None  
  
    def _check_found(self, analysis_text):  
        """检查是否找到目标物品"""  
        if not analysis_text:  
            return False  
          
        # 检查包含"有"的肯定回答  
        positive_keywords = ["找到", "是", "找到了","found"]
          
        for keyword in positive_keywords:  
            if keyword in analysis_text:  
                return True  
          
        return False  
        
  
    def video_capture_thread(self):      
        """视频捕获线程 - 增强异常处理"""      
        capture_interval = 0.5   

        frame_count = 0  # ✅ 添加这行   
        
        while self.search_active and not self.found:      
            try:  
                # 新增: 进度更新逻辑  
                if self.progress_callback and frame_count % 5 == 0:  
                    progress = min(50 + frame_count * 2, 90)  # 50-90%  
                    self.progress_callback(progress)  
                
                frame_count += 1  # 新增: 每次循环递增

                
                # 在循环开始时检查状态  
                if not self.search_active or self.found:  
                    break  
                    
                ret, frame = self.cap.read()      
                if not ret:      
                    logger.warning("无法读取摄像头帧")      
                    # 改进的等待机制  
                    for _ in range(int(capture_interval * 10)):  
                        if not self.search_active or self.found:  
                            break  
                        time.sleep(0.1)  
                    continue    
                    
                cv2.imshow("Search Camera", frame)      
                
                key = cv2.waitKey(1) & 0xFF      
                if key == ord('q') or chr(key).lower() == 'q':    
                    print("\n[键盘输入] 检测到'q'键，正在停止搜索...")      
                    with self.lock:      
                        self.search_active = False      
                    break    
                
                print(f"[分析开始] 发送图片到远程服务器识别 {self.target_item}...")      
                result = self._send_frame_to_analysis(frame)      
                
                if result:      
                    analysis_text = self._parse_result(result)      
                    if analysis_text:      
                        print(f"\n[--搜索结果] {analysis_text}")      
                        
                        if self._check_found(analysis_text):      
                            try:    
                                with self.lock:      
                                    self.found = True      
                                    self.search_active = False      
                                    self.result_message = "成功找到" + str(self.target_item) + "！" + str(analysis_text)  
                                    
                                    # 安全停止机器人    
                                    try:    
                                        self.clbrobot.t_stop(0)    
                                    except Exception as robot_error:    
                                        logger.error(f"机器人停止失败: {robot_error}")    
                                        print(f"[警告] 机器人停止失败，但搜索完成: {robot_error}")    
                                    
                                return self.result_message    
                            except Exception as lock_error:    
                                logger.error(f"线程锁操作失败: {lock_error}")    
                                # 即使锁失败，也尝试返回结果    
                                return f"成功找到{self.target_item}！{analysis_text}（注意：线程同步异常）"    
                                
                else:      
                    print("[识别失败] 无法获取识别结果")      
                
                # 改进的等待机制  
                for _ in range(int(capture_interval * 10)):  
                    if not self.search_active or self.found:  
                        break  
                    time.sleep(0.1)  
                    
            except Exception as e:      
                logger.error(f"视频捕获线程错误: {e}")      
                print(f"[异常] 视频捕获错误: {e}")    
                
                # 检查是否是关键异常    
                if "camera" in str(e).lower() or "opencv" in str(e).lower():    
                    print("[严重] 摄像头相关异常，退出搜索")    
                    break  
                
                # 改进的等待机制  
                for _ in range(int(capture_interval * 10)):  
                    if not self.search_active or self.found:  
                        break  
                    time.sleep(0.1)  
        
        # 安全的循环结束处理    
        try:    
            if self.found:      
                return self.result_message      
            else:      
                return f"经过搜索，没有找到{self.target_item}"    
        except Exception as final_error:    
            logger.error(f"最终结果处理异常: {final_error}")    
            return f"搜索完成，但结果处理异常: {final_error}"


    def movement_thread(self):    
        """机器人运动控制线程 - 改进版本，提高响应性"""    
        movements = [    
            ("前进2步", lambda: self.clbrobot.t_up(50, 2)),    
            ("左转", lambda: self.clbrobot.turnLeft(50, 1)),    
            ("向右2步", lambda: self.clbrobot.moveRight(50, 2)),    
            ("左转", lambda: self.clbrobot.turnLeft(50, 1)),    
            ("后退2步", lambda: self.clbrobot.t_down(50, 2)),    
            ("左转", lambda: self.clbrobot.turnLeft(50, 1)),    
            ("向左2步", lambda: self.clbrobot.moveLeft(50, 2)),    
            ("左转", lambda: self.clbrobot.turnLeft(50, 1)),    
            ("前进2步", lambda: self.clbrobot.t_up(50, 2))    
        ]    
        
        movement_index = 0    
        cycle_count = 0    
        max_cycles = 10  # 限制为一轮循环    
        action_interval = 3  
        
        while self.search_active and not self.found and cycle_count < max_cycles:    
            try:    
                # 在获取锁前先检查状态  
                if not self.search_active or self.found:  
                    break  
                    
                with self.lock:    
                    if not self.found and self.search_active and cycle_count < max_cycles:    
                        action_name, action_func = movements[movement_index % len(movements)]    
                        logger.info(f"执行动作: {action_name}")    
                        action_func()    
                        movement_index += 1    
                        
                        # 检查是否完成一轮循环    
                        if movement_index % len(movements) == 0:    
                            cycle_count += 1    
                            print(f"[运动控制] 完成第{cycle_count}轮运动循环")    
                
                # 改进的等待机制 - 每0.1秒检查一次状态  
                for _ in range(action_interval * 10):    
                    if not self.search_active or self.found:  
                        break  
                    time.sleep(0.1)    
                        
            except Exception as e:    
                logger.error(f"运动控制线程错误: {e}")    
                # 出错时也要检查状态  
                for _ in range(action_interval * 10):    
                    if not self.search_active or self.found:  
                        break  
                    time.sleep(0.1)  
        
        # 确保机器人安全停止  
        try:  
            self.clbrobot.t_stop(0)  
            logger.info("机器人已安全停止")  
        except Exception as e:  
            logger.error(f"机器人停止失败: {e}")  
        
        print("运动控制线程已结束")

    def __del__(self):      
        """清理资源 - 改进版本"""      
        try:  
            # 确保搜索停止  
            with self.lock:  
                self.search_active = False  
                self.found = True  # 强制结束线程  
        except:  
            pass  
        
        # 释放摄像头资源  
        if hasattr(self, 'cap') and self.cap is not None:      
            try:  
                self.cap.release()      
                cv2.destroyAllWindows()      
                logger.info("摄像头资源已释放")  
            except Exception as e:  
                logger.error(f"摄像头资源释放失败: {e}")


def search_item(arguments: dict) -> str:  
    """启动物品搜索任务,立即返回任务ID"""  
    target_item = arguments.get("target_item", "")  
      
    if not target_item:  
        return json.dumps({"error": "缺少参数: target_item"})  
      
    # 生成任务ID  
    task_id = str(uuid.uuid4())[:8]  
      
    # 创建任务状态  
    task_state = {  
        "id": task_id,  
        "target": target_item,  
        "status": "running",  # running/found/not_found/error/cancelled  
        "progress": 0,  # 0-100  
        "result": "",  
        "start_time": time.time()  
    }  
      
    with _search_lock:  
        _active_searches[task_id] = task_state  
      
    # 后台线程执行搜索  
    def _background_search():  
        try:  
            result = _execute_search_sync(target_item, task_state)  
              
            with _search_lock:  
                if "找到" in result or "found" in result.lower():  
                    task_state["status"] = "found"  
                else:  
                    task_state["status"] = "not_found"  
                task_state["result"] = result  
                task_state["progress"] = 100  
                  
        except Exception as e:  
            with _search_lock:  
                task_state["status"] = "error"  
                task_state["result"] = str(e)  
                task_state["progress"] = 100  
      
    # 启动后台线程  
    search_thread = threading.Thread(target=_background_search, daemon=True)  
    search_thread.start()  
      
    logger.info(f"搜索任务已启动: {task_id} - {target_item}")  
      
    return json.dumps({  
        "task_id": task_id,  
        "message": f"搜索任务已启动: {target_item}",  
        "status": "running"  
    }, ensure_ascii=False)



def _execute_search_sync(target_item: str, task_state: dict) -> str:  
    """同步执行搜索 - 内部函数"""  
    import os  
    import threading  
    import traceback  
      
    os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'  
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'  # 新增: 无头模式  
      
    clbrobot = None  
    searcher = None  
    movement_thread = None  
      
    def update_progress(progress):  
        """进度更新回调"""  
        with _search_lock:  
            task_state["progress"] = progress  
      
    try:  
        print(f"\n=== 开始搜索物品: {target_item} (视频捕获+运动控制) ===")  
          
        if LOBOROBOT is None:  
            raise RuntimeError("机器人控制库不可用")  
          
        # 更新进度: 初始化  
        update_progress(10)  
          
        clbrobot = LOBOROBOT()  
        searcher = ConcurrentSearcher(None, clbrobot, target_item,   
                                     progress_callback=update_progress,  
                                     task_state=task_state)  
          
        # 更新进度: 启动运动  
        update_progress(20)  
          
        movement_thread = threading.Thread(target=searcher.movement_thread)  
        movement_thread.daemon = False  
        movement_thread.start()  
        print("运动控制线程已启动")  
          
        # 更新进度: 开始视频捕获  
        update_progress(30)  
          
        # 移除 cv2.imshow 调用 (在 video_capture_thread 中注释掉)  
        video_result = searcher.video_capture_thread()  
          
        # 等待运动线程结束  
        if movement_thread and movement_thread.is_alive():  
            movement_thread.join(timeout=5.0)  
          
        # 更新进度: 完成  
        update_progress(100)  
          
        return video_result  
          
    except Exception as e:  
        error_msg = f"搜索过程中出现错误: {str(e)}"  
        logger.error(error_msg)  
        logger.error(traceback.format_exc())  
          
        try:  
            if clbrobot is not None:  
                clbrobot.t_stop(0)  
        except:  
            pass  
          
        raise Exception(error_msg)  
          
    finally:  
        try:  
            if searcher is not None:  
                with searcher.lock:  
                    searcher.search_active = False  
                    searcher.found = True  
              
            if movement_thread and movement_thread.is_alive():  
                movement_thread.join(timeout=2.0)  
              
            if searcher is not None:  
                searcher.__del__()  
        except Exception as cleanup_error:  
            logger.error(f"资源清理失败: {cleanup_error}")


def get_search_status(arguments: dict) -> str:  
    """查询搜索任务状态和进度"""  
    task_id = arguments.get("task_id", "")  
      
    if not task_id:  
        return json.dumps({"error": "缺少参数: task_id"})  
      
    with _search_lock:  
        if task_id not in _active_searches:  
            return json.dumps({"error": f"任务不存在: {task_id}"})  
          
        task = _active_searches[task_id].copy()  
      
    # 计算运行时间  
    elapsed = time.time() - task["start_time"]  
      
    return json.dumps({  
        "task_id": task["id"],  
        "target": task["target"],  
        "status": task["status"],  
        "progress": task["progress"],  
        "result": task["result"],  
        "elapsed_seconds": round(elapsed, 1)  
    }, ensure_ascii=False)


def cancel_search(arguments: dict) -> str:  
    """取消正在运行的搜索任务"""  
    task_id = arguments.get("task_id", "")  
      
    if not task_id:  
        return json.dumps({"error": "缺少参数: task_id"})  
      
    with _search_lock:  
        if task_id not in _active_searches:  
            return json.dumps({"error": f"任务不存在: {task_id}"})  
          
        task = _active_searches[task_id]  
          
        if task["status"] in ["found", "not_found", "error"]:  
            return json.dumps({  
                "message": f"任务已完成,无法取消",  
                "status": task["status"]  
            }, ensure_ascii=False)  
          
        task["status"] = "cancelled"  
        task["result"] = "任务已被用户取消"  
        task["progress"] = 100  
      
    logger.info(f"搜索任务已取消: {task_id}")  
      
    return json.dumps({  
        "task_id": task_id,  
        "message": "任务已取消"  
    }, ensure_ascii=False)