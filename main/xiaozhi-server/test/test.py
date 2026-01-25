import websocket  
import json  
import uuid  
import time  
import threading  
  
class XiaoZhiWebSocketClient:  
    def __init__(self, url, token, device_id, client_id=None, version=1):  
        self.url = url  
        self.token = token  
        self.device_id = device_id  
        self.client_id = client_id or str(uuid.uuid4())  
        self.version = version  
        self.ws = None  
        self.session_id = None  
        self.connected = False  
          
    def connect(self):  
        """建立WebSocket连接"""  
        try:  
            # 构造必需的headers  
            headers = {  
                "Authorization": f"Bearer {self.token}" if not self.token.startswith("Bearer ") else self.token,  
                "Protocol-Version": str(self.version),  
                "Device-Id": self.device_id,  
                "Client-Id": self.client_id  
            }  
              
            # 创建WebSocket连接，启用二进制模式  
            self.ws = websocket.WebSocketApp(  
                self.url,  
                header=headers,  
                on_open=self._on_open,  
                on_message=self._on_message,  
                on_error=self._on_error,  
                on_close=self._on_close  
            )  
              
            # 启动连接线程  
            wst = threading.Thread(target=self.ws.run_forever)  
            wst.daemon = True  
            wst.start()  
              
            # 等待连接完成  
            timeout = 10  
            while not self.connected and timeout > 0:  
                time.sleep(0.1)  
                timeout -= 0.1  
                  
            return self.connected  
              
        except Exception as e:  
            print(f"连接失败: {e}")  
            return False  
      
    def _on_open(self, ws):  
        """连接建立回调"""  
        print("WebSocket连接已建立")  
        hello_message = self._get_hello_message()  
        ws.send(hello_message)  
      
    def _on_message(self, ws, message):  
        """消息接收回调 - 修复二进制数据处理"""  
        # 检查是否为字符串（JSON消息）  
        if isinstance(message, str):  
            try:  
                data = json.loads(message)  
                msg_type = data.get("type")  
                  
                if msg_type == "hello" and data.get("transport") == "websocket":  
                    self.session_id = data.get("session_id")  
                    self.connected = True  
                    print(f"连接成功，Session ID: {self.session_id}")  
                elif msg_type == "stt":  
                    print(f"语音识别结果: {data.get('text')}")  
                elif msg_type == "tts":  
                    state = data.get("state")  
                    if state == "start":  
                        print("开始播放TTS音频")  
                    elif state == "stop":  
                        print("TTS播放结束")  
                    elif state == "sentence_start":  
                        print(f"播放句子: {data.get('text')}")  
                elif msg_type == "llm":  
                    print(f"LLM响应: {data.get('text')}")  
                elif msg_type == "mcp":  
                    print(f"MCP消息: {data.get('payload')}")  
                else:  
                    print(f"收到JSON消息: {message}")  
                      
            except json.JSONDecodeError as e:  
                print(f"JSON解析错误: {e}")  
                print(f"原始消息: {message}")  
          
        # 处理二进制数据（音频）  
        elif isinstance(message, bytes):  
            print(f"收到音频数据: {len(message)} 字节")  
            # 这里可以添加音频数据处理逻辑  
            # 例如保存到文件或解码播放  
            self._handle_audio_data(message)  
          
        else:  
            print(f"收到未知类型消息: {type(message)}")  
      
    def _handle_audio_data(self, audio_data):  
        """处理音频数据"""  
        # 根据协议版本解析音频数据  
        if self.version == 2:  
            # BinaryProtocol2格式  
            if len(audio_data) >= 16:  # 至少包含头部  
                import struct  
                version, msg_type, reserved, timestamp, payload_size = struct.unpack("!HHII", audio_data[:16])  
                payload = audio_data[16:16+payload_size]  
                print(f"协议版本2: 类型={msg_type}, 时间戳={timestamp}, 音频数据={len(payload)}字节")  
        elif self.version == 3:  
            # BinaryProtocol3格式  
            if len(audio_data) >= 4:  # 至少包含头部  
                import struct  
                msg_type, reserved, payload_size = struct.unpack("!BBH", audio_data[:4])  
                payload = audio_data[4:4+payload_size]  
                print(f"协议版本3: 类型={msg_type}, 音频数据={len(payload)}字节")  
        else:  
            # 版本1：直接是OPUS数据  
            print(f"协议版本1: OPUS音频数据={len(audio_data)}字节")  
      
    def _on_error(self, ws, error):  
        """错误回调"""  
        print(f"WebSocket错误: {error}")  
      
    def _on_close(self, ws, close_status_code, close_msg):  
        """连接关闭回调"""  
        print("WebSocket连接已关闭")  
        self.connected = False  
      
    def _get_hello_message(self):  
        """构造hello消息"""  
        return json.dumps({  
            "type": "hello",  
            "version": self.version,  
            "features": {  
                "mcp": True  
            },  
            "transport": "websocket",  
            "audio_params": {  
                "format": "opus",  
                "sample_rate": 16000,  
                "channels": 1,  
                "frame_duration": 60  
            }  
        })  
      
    def send_message(self, message):  
        """发送消息"""  
        if self.ws and self.connected:  
            self.ws.send(json.dumps(message))  
      
    def send_audio_data(self, audio_data):  
        """发送音频数据"""  
        if not self.ws or not self.connected:  
            return False  
              
        if self.version == 2:  
            # 使用BinaryProtocol2格式  
            import struct  
            timestamp = int(time.time() * 1000)  
            header = struct.pack(  
                "!HHII",  
                2,  # version  
                0,  # type (0=OPUS)  
                0,  # reserved  
                timestamp,  
                len(audio_data)  
            )  
            self.ws.send(header + audio_data, websocket.ABNF.OPCODE_BINARY)  
        elif self.version == 3:  
            # 使用BinaryProtocol3格式  
            import struct  
            header = struct.pack(  
                "!BBH",  
                0,  # type (0=OPUS)  
                0,  # reserved  
                len(audio_data)  
            )  
            self.ws.send(header + audio_data, websocket.ABNF.OPCODE_BINARY)  
        else:  
            # 版本1：直接发送音频数据  
            self.ws.send(audio_data, websocket.ABNF.OPCODE_BINARY)  
        return True  
      
    def close(self):  
        """关闭连接"""  
        if self.ws:  
            self.ws.close()  
  
# 使用示例  
def main():  
    url = "ws://1.12.222.251:6008/xiaozhi/v1/ws"  
    token = "CR9QRWgrZm7Q_PGsQ75CFyCtTR8XCEkpxMWZ23cwmUA.1769082687"  
    device_id = "a4:69:68:d2:e9:ee"  
    client_id = "3870e010-2040-4000-b6fe-2ba83ae69123"  
      
    client = XiaoZhiWebSocketClient(url, token, device_id, client_id, version=1)  
      
    if client.connect():  
        print("客户端连接成功")  
          
        # 发送开始监听消息  
        client.send_message({  
            "session_id": client.session_id,  
            "type": "listen",  
            "state": "start",  
            "mode": "auto"  
        })  
          
        # 保持连接  
        try:  
            while client.connected:  
                time.sleep(1)  
        except KeyboardInterrupt:  
            print("用户中断")  
        finally:  
            client.close()  
    else:  
        print("连接失败")  
  
if __name__ == "__main__":  
    main()