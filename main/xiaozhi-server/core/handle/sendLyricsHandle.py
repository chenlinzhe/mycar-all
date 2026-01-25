import asyncio
import time
import re
from typing import Dict
from pathlib import Path
from core.handle.sendAudioHandle import send_stt_message
from core.providers.tts.dto.dto import TTSMessageDTO, SentenceType, ContentType
from core.utils.dialogue import Message
from mutagen.mp3 import MP3
from websockets.exceptions import ConnectionClosedError

TAG = __name__

# 全局状态变量
_current_music_path = None
_lyrics_dict = {}
_is_running = False
_start_time = 0

async def start_lyrics_sync(conn, music_path: str):
    """启动歌词同步"""
    global _current_music_path, _lyrics_dict, _is_running, _start_time

    # 延时xxx秒开始推送
    # 歌词偏移量
    await asyncio.sleep(2) 

    conn.logger.bind(tag=TAG).info(f"开始初始化歌词同步 | 音乐路径: {music_path}")
    _current_music_path = music_path
    _lyrics_dict = _parse_lyrics(conn, music_path)
    conn.logger.bind(tag=TAG).info(f"解析到{len(_lyrics_dict)}条歌词")
    
    _is_running = True
    _start_time = time.time()
    
    # 获取真实音乐时长
    duration = _get_music_duration(conn, music_path)  # 传入音频文件路径
    
    try:
        while time.time() - _start_time < duration and _is_running:
            # 检查连接状态和停止事件
            if conn.stop_event and conn.stop_event.is_set():
                conn.logger.bind(tag=TAG).info("检测到停止事件，结束歌词同步")
                break
            
            # 检查WebSocket连接状态
            if hasattr(conn, 'websocket') and conn.websocket:
                if hasattr(conn.websocket, 'closed') and conn.websocket.closed:
                    conn.logger.bind(tag=TAG).info("WebSocket连接已关闭，结束歌词同步")
                    break
                elif hasattr(conn.websocket, 'state') and conn.websocket.state.name == 'CLOSED':
                    conn.logger.bind(tag=TAG).info("WebSocket连接已关闭，结束歌词同步")
                    break
            
            current_pos = time.time() - _start_time
            await _send_lyric(conn, current_pos)
            await asyncio.sleep(0.1) # 延时，默认0.1
    except asyncio.CancelledError:
        conn.logger.bind(tag=TAG).info("歌词同步任务被取消")
        raise
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"歌词同步任务异常: {str(e)}")
    finally:
        _is_running = False
        conn.logger.bind(tag=TAG).info("歌词同步任务结束")

def _parse_lyrics(conn, music_path):
    """解析目录下的歌词文件"""
    lrc_path = Path(music_path).with_suffix('.lrc')
    conn.logger.bind(tag=TAG).info(f"尝试加载歌词文件: {lrc_path}")
    lyrics = {}
    
    if lrc_path.exists():
        with open(lrc_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 匹配时间标签 [mm:ss.xx] 或 [mm:ss.xxx]
                if not line.startswith('[') or ']' not in line:
                    continue
                    
                try:
                    time_part, text_part = line.split(']', 1)
                    time_str = time_part[1:]  # 去除左括号
                    
                    # 确保是时间格式而非其他标签
                    if ':' in time_str and time_str.replace(':', '').replace('.', '').isdigit():
                        if '.' in time_str:
                            minutes, rest = time_str.split(':', 1)
                            seconds = rest.split('.')[0]
                        else:
                            minutes, seconds = time_str.split(':', 1)
                            
                        # 转换为浮点秒数
                        total_sec = float(minutes) * 60 + float(seconds)
                        lyrics[total_sec] = text_part.strip()
                except (ValueError, IndexError) as e:
                    conn.logger.bind(tag=TAG).error(f"跳过无效行: {line} - 错误: {str(e)}")
                    continue
    return lyrics

async def _send_lyric(conn, current_pos: float):
    """发送歌词"""
    global _lyrics_dict, _is_running
    conn.logger.bind(tag=TAG).debug(f"当前播放位置: {current_pos:.1f}s")
    
    # 检查连接状态
    if not _is_running:
        return
    
    if conn.stop_event and conn.stop_event.is_set():
        _is_running = False
        return
    
    # 检查WebSocket连接状态
    if hasattr(conn, 'websocket') and conn.websocket:
        if hasattr(conn.websocket, 'closed') and conn.websocket.closed:
            _is_running = False
            return
        elif hasattr(conn.websocket, 'state') and conn.websocket.state.name == 'CLOSED':
            _is_running = False
            return
    
    # 优化时间匹配逻辑
    valid_times = [t for t in _lyrics_dict.keys() if t <= current_pos]
    if not valid_times:
        return
    
    closest_time = max(valid_times)  # 改为找最大的小于当前时间的时间点
    if _lyrics_dict.get(closest_time):
        try:
            await send_stt_message(conn, f"{_lyrics_dict[closest_time]}")
            conn.logger.bind(tag=TAG).info(f"已发送歌词: {_lyrics_dict[closest_time]}")
            del _lyrics_dict[closest_time]
        except ConnectionClosedError:
            conn.logger.bind(tag=TAG).warning("WebSocket连接已关闭，停止发送歌词")
            _is_running = False
        except Exception as e:
            conn.logger.bind(tag=TAG).error(f"发送歌词失败: {str(e)}")
            # 如果是连接相关错误，停止任务
            if "close" in str(e).lower() or "closed" in str(e).lower():
                _is_running = False

def _get_music_duration(conn, file_path: str) -> float:
    """获取音乐真实时长（秒）"""
    try:
        audio = MP3(file_path)
        if audio.info.length > 0:
            conn.logger.bind(tag=TAG).info(f"歌曲时长: {audio.info.length}秒")
            return audio.info.length
        return 300  # 默认5分钟
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"获取音频时长失败: {str(e)}")
        return 300  # 降级为默认值

async def stop_lyrics_sync(conn):
    """停止歌词推送"""
    global _is_running
    _is_running = False
    conn.logger.bind(tag=__name__).info("歌词推送已中止")