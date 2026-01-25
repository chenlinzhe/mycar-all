#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
    Modified on Fri Oct 20 2024
    @author: ChatGPT
"""
from aip import AipSpeech
import pygame
import os
from time import time
from pydub import AudioSegment
from pydub.playback import play

# 百度云账号信息
baidu_APP_ID = '25632264'
baidu_API_KEY = 'O7LQkfkZqrAjALleKk5GbuU7'
baidu_SECRET_KEY = '5234KGD6IkVN1uID32lGZwF1ghYU2LCQ'

# 初始化百度语音合成客户端
baidu_aipSpeech = AipSpeech(baidu_APP_ID, baidu_API_KEY, baidu_SECRET_KEY)

# 生成语音
t1 = time()
# result = baidu_aipSpeech.synthesis(text='陈俊皓、起床啦！陈俊皓、起床啦！陈俊皓、起床啦！陈小福、起床啦！陈小福、起床啦！陈小福、起床啦',
#                                    options={'spd': 1, 'vol': 18, 'per': 0})

result = baidu_aipSpeech.synthesis(text='邋遢皓、起床啦！邋遢皓、起床啦！邋遢皓、起床啦！邋遢福、起床啦！邋遢福、起床啦！邋遢福、起床啦',
                                   options={'spd': 1, 'vol': 18, 'per': 0})

# 保存合成的语音为文件
result_file = 'result.mp3'
if not isinstance(result, dict):
    with open(result_file, 'wb') as f:
        f.write(result)
else:
    print(result)

# 加载 MP3 音频文件并切割为 10 段
audio_file = 'teqjxq.mp3'  # 输入的原始音频文件
if os.path.exists(audio_file):
    print("加载音频文件...")
    audio = AudioSegment.from_mp3(audio_file)
    
    # 切割音频为 10 段
    duration = len(audio)  # 获取音频总时长（毫秒）
    segment_duration = duration // 10  # 每段的时长

    segments = [audio[i*segment_duration:(i+1)*segment_duration] for i in range(10)]
    print("音频文件切割为10段，每段时长约 {} 秒".format(segment_duration / 1000.0))

    # 加载插入的 result 音频
    if os.path.exists(result_file):
        result_audio = AudioSegment.from_mp3(result_file)
    else:
        print("合成音频文件不存在，请检查路径")
        exit(1)

    # 将 result 插入到每段之间
    final_audio = segments[0]
    for i in range(1, 10):
        final_audio += result_audio + segments[i]

    # 保存最终合成的音频文件
    output_file = 'final_output.mp3'
    final_audio.export(output_file, format='mp3')
    print("合成的音频已保存为 {}".format(output_file))
    
    # 使用 pygame 播放音频
    pygame.mixer.init()
    if not pygame.mixer.get_init():
        print("pygame mixer 初始化失败")
    else:
        print("pygame mixer 初始化成功，准备播放音频")
    
    # 播放合成后的音频
    pygame.mixer.music.load(output_file)
    pygame.mixer.music.set_volume(1.0)
    pygame.mixer.music.play()
    
    # 等待音频播放完成
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)  # 每100毫秒检查一次
else:
    print("原始音频文件不存在，请检查路径")

t2 = time()
print("总耗时: {} 秒".format(t2 - t1))
