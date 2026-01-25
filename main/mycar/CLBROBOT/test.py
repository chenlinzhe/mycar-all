# -*- coding: utf-8 -*-


import cv2
import os

# 创建保存图片的目录
output_dir = 'test_images'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# 初始化摄像头
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("错误: 无法打开摄像头。")
    exit()

# 读取一帧
ret, frame = cap.read()
if ret:
    # 保存图片
    img_name = "{}/test_image.png".format(output_dir)
    cv2.imwrite(img_name, frame)
    print("成功保存图片: {}".format(img_name))
else:
    print("错误: 捕获视频帧失败。")

# 显示当前帧图像
cv2.imshow('Test Camera', frame)
cv2.waitKey(0)  # 等待按键
cap.release()  # 释放摄像头资源
cv2.destroyAllWindows()  # 关闭所有窗口
