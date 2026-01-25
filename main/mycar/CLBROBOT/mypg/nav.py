# -*- coding: utf-8 -*-
import os
import time
import cv2
import numpy as np
from LOBOROBOT import LOBOROBOT  # 载入机器人库
import RPi.GPIO as GPIO

# 实例化机器人对象
clbrobot = LOBOROBOT()

# 加载保存的图片
def load_images_from_folder(folder):
    images = []
    for filename in os.listdir(folder):
        img_path = os.path.join(folder, filename)
        img = cv2.imread(img_path)
        if img is not None:
            images.append(img)
    return images

# 识别图像中的特征
def recognize_features(images):
    orb = cv2.ORB_create()
    keypoints_list = []
    
    for img in images:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        keypoints, _ = orb.detectAndCompute(gray, None)
        keypoints_list.append((img, keypoints))
    
    return keypoints_list

# 移动到指定的距离
def move_forward(distance):
    speed = 50  # 假设速度为50
    duration = distance / speed
    clbrobot.t_up(speed, duration)
    clbrobot.t_stop(1)

def turn_right():
    clbrobot.turnRight(50, 1)
    clbrobot.t_stop(1)

try:
    print("加载图像...")
    images = load_images_from_folder('slam_images')
    keypoints_list = recognize_features(images)

    # 从A点出发
    print("从A点出发...")
    move_forward(100)  # 移动到B点
    print("已到达B点，准备右转...")
    turn_right()  # 右转
    print("右转完成，移动到C点...")
    move_forward(100)  # 移动到C点
    print("已到达C点。")

    # 你可以在这里添加更多逻辑来处理图像特征识别和导航

except KeyboardInterrupt:
    pass

finally:
    clbrobot.t_stop(0)  # 停止小车
    GPIO.cleanup()  # 清理GPIO
