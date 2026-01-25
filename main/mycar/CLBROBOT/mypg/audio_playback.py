#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pyaudio
import wave
import os
import audioop

# 设置录音和放大后的文件名
OUTPUT_FILENAME = "recording.wav"
AMPLIFIED_FILENAME = "recording_loud.wav"

# 设置系统音量为最大
os.system("amixer -c 1 set PCM 100%")

# 设置参数
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 8192
AMPLIFICATION_FACTOR = 2  # 放大倍数，可调节音量

# 初始化 PyAudio
p = pyaudio.PyAudio()

# 自动检测 USB 设备并设置设备索引
def get_device_index():
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        if "USB" in dev_info['name']:
            print(f"使用 USB 设备，设备索引为: {i}")
            return i, int(dev_info["defaultSampleRate"])
    return 0, RATE

input_device_index, RATE = get_device_index()

# 录音函数
def record_audio():
    frames = []
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                    input=True, frames_per_buffer=CHUNK, input_device_index=input_device_index)
    print("开始录音...按下回车键结束录音")
    input("按下回车键开始录音...")
    try:
        while True:
            frames.append(stream.read(CHUNK, exception_on_overflow=False))
    except KeyboardInterrupt:
        pass
    finally:
        stream.stop_stream()
        stream.close()
    return frames

# 保存音频文件
def save_audio(frames, filename):
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

# 播放音频文件
def play_audio(filename):
    print(f"播放 {filename} ...")
    os.system(f"aplay {filename}")

# 主程序
if __name__ == "__main__":
    # 录音并保存
    frames = record_audio()
    save_audio(frames, OUTPUT_FILENAME)
    print(f"录音已保存为 {OUTPUT_FILENAME}")

    # 放大音量
    amplified_frames = [audioop.mul(frame, 2, AMPLIFICATION_FACTOR) for frame in frames]
    save_audio(amplified_frames, AMPLIFIED_FILENAME)
    print(f"放大后的录音已保存为 {AMPLIFIED_FILENAME}")

    # 播放放大后的音频
    play_audio(AMPLIFIED_FILENAME)

    # 使用 sox 进一步放大音频文件
    FINAL_FILENAME = "final_output.wav"
    os.system(f"sox {AMPLIFIED_FILENAME} {FINAL_FILENAME} vol 3.0")
    print(f"最终的放大音频保存为 {FINAL_FILENAME}")
    play_audio(FINAL_FILENAME)

    # 关闭 PyAudio
    p.terminate()
