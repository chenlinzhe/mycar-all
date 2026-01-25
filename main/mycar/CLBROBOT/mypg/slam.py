# -*- coding: utf-8 -*-
import cv2
import numpy as np
import os
import random
import time
from LOBOROBOT import LOBOROBOT  # 载入机器人库
import RPi.GPIO as GPIO

# 创建保存图片的目录
output_dir = 'slam_images'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# 实例化机器人对象
clbrobot = LOBOROBOT()

# 舵机的初始角度设置
base_servo_angle = 90  # 底座舵机初始角度
top_servo_angle = 0    # 顶部舵机初始角度
clbrobot.set_servo_angle(9, base_servo_angle)  # 底座舵机初始化
time.sleep(1)  # 增加延时
clbrobot.set_servo_angle(10, top_servo_angle)  # 顶部舵机初始化
time.sleep(1)

# 初始化摄像头
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("错误: 无法打开摄像头。")
    exit()

# 创建ORB特征检测器
orb = cv2.ORB_create()

# 初始化一个空的地图
map_image = np.zeros((480, 640, 3), dtype=np.uint8)
frame_count = 0

# 运动命令列表
commands = [
    lambda: clbrobot.t_up(50, 1),      # 前进
    lambda: clbrobot.t_down(50, 1),    # 后退
    lambda: clbrobot.turnLeft(50, 1),  # 左转
    lambda: clbrobot.turnRight(50, 1), # 右转
]

# 定义避障函数
def avoid_obstacle():
    print("检测到障碍物，进行避让...")
    clbrobot.t_down(50, 1)  # 后退
    time.sleep(1)  # 后退一秒
    clbrobot.turnLeft(50, 1)  # 左转
    clbrobot.t_stop(1)  # 停止
    clbrobot.t_up(50, 1)  # 前进

try:
    is_avoiding = False  # 避障状态标志
    while True:
        # 读取摄像头帧
        ret, frame = cap.read()
        if not ret:
            print("错误: 捕获视频帧失败。")
            break

        # 显示当前帧图像
        cv2.imshow('Robot Camera', frame)

        # 检测障碍物（简单阈值法）
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)

        # 检查是否有明显的障碍物
        obstacle_detected = np.sum(edges) > 5000000  # 自定义阈值

        if obstacle_detected and not is_avoiding:
            avoid_obstacle()
            is_avoiding = True  # 进入避障状态
        elif not obstacle_detected and is_avoiding:
            is_avoiding = False  # 退出避障状态
            print("退出避让")  # 输出退出避让信息
        elif not is_avoiding:
            # 随机选择一个运动命令并执行
            command = random.choice(commands)
            command()  # 执行运动命令
            clbrobot.t_stop(1)  # 停止运动

            # 检测关键点和描述符
            keypoints, descriptors = orb.detectAndCompute(gray, None)

            # 更新地图
            if keypoints:
                for kp in keypoints:
                    x, y = int(kp.pt[0]), int(kp.pt[1])
                    cv2.circle(map_image, (x, y), 2, (0, 0, 255), -1)

            # 显示地图
            cv2.imshow('Map', map_image)

            # 自动保存当前帧的图片
            img_name = "{}/frame_{}.png".format(output_dir, frame_count)
            cv2.imwrite(img_name, frame)
            print("保存图片: {}".format(img_name))
            frame_count += 1

        # 检查按键
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    pass

finally:
    clbrobot.t_stop(0)  # 停止小车
    GPIO.cleanup()
    cap.release()  # 释放摄像头资源
    cv2.destroyAllWindows()  # 关闭所有窗口
