import requests  
import json  
  
def get_ota_config(device_mac, client_id):  
    """从OTA接口获取WebSocket配置"""  
    ota_url = "http://你的服务器:8002/xiaozhi/ota/"  
      
    headers = {  
        "Device-Id": device_mac,  # 设备MAC地址  
        "Client-Id": client_id,   # 客户端ID  
        "Content-Type": "application/json"  
    }  
      
    data = {  
        "application": {  
            "version": "1.0.1",  
            "elf_sha256": "固件hash"  
        },  
        "board": {  
            "mac": device_mac,  
            "type": "ESP32-S3-BOX"  
        }  
    }  
      
    response = requests.post(ota_url, headers=headers, json=data)  
      
    if response.status_code == 200:  
        config = response.json()  
        return config  
    else:  
        print(f"OTA请求失败: {response.status_code}")  
        return None



"""OTA接口返回的JSON格式如下
{  
  "websocket": {  
    "url": "ws://192.168.1.25:8000/xiaozhi/v1/",  
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  
  }  
}


"""

#解析代码：
def parse_ota_config(config):  
    """解析OTA返回的配置"""  
    if "websocket" in config:  
        ws_config = config["websocket"]  
        ws_url = ws_config["url"]  
        token = ws_config["token"]  
        return ws_url, token  
    else:  
        print("未找到websocket配置")  
        return None, None






#使用获取的URL和token建立WebSocket连接 ：


import asyncio  
import websockets  
import json  
  
async def connect_to_websocket(ws_url, token, device_mac):  
    """连接到WebSocket服务器"""  
    headers = {  
        "device-id": device_mac,  
        "authorization": f"Bearer {token}"  
    }  
      
    try:  
        async with websockets.connect(ws_url, extra_headers=headers) as websocket:  
            print("WebSocket连接成功")  
              
            # 等待服务器hello消息  
            hello_msg = await websocket.recv()  
            print(f"服务器消息: {hello_msg}")  
              
            # 开始通信循环  
            await handle_communication(websocket)  
              
    except Exception as e:  
        print(f"WebSocket连接失败: {e}")









  
async def handle_communication(websocket):  
    """处理WebSocket通信"""  
    while True:  
        try:  
            # 接收服务器消息  
            message = await websocket.recv()  
              
            if isinstance(message, bytes):  
                # 音频数据  
                print("收到音频数据，播放...")  
                # play_audio(message)  
            else:  
                # 文本消息  
                msg_data = json.loads(message)  
                print(f"收到文本消息: {msg_data}")  
                  
        except websockets.exceptions.ConnectionClosed:  
            print("WebSocket连接已关闭")  
            break  
        except Exception as e:  
            print(f"通信错误: {e}")  
            break



async def device_main():  
    """设备端主流程"""  
    device_mac = "11:22:33:44:55:66"  # 设备MAC地址  
    client_id = "device_client_001"    # 客户端ID  
      
    # 1. 获取OTA配置  
    ota_config = get_ota_config(device_mac, client_id)  
    if not ota_config:  
        return  
      
    # 2. 解析配置  
    ws_url, token = parse_ota_config(ota_config)  
    if not ws_url or not token:  
        return  
      
    # 3. 连接WebSocket  
    await connect_to_websocket(ws_url, token, device_mac)  