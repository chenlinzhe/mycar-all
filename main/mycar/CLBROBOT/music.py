# -*- coding: utf-8 -*-
import pygame

pygame.mixer.init()
pygame.mixer.music.load('土耳其进行曲.mp3')
pygame.mixer.music.play()

while pygame.mixer.music.get_busy():  # 等待音乐播放完
    pygame.time.Clock().tick(10)
