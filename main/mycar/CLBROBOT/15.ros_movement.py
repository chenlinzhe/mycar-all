#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import rospy
from std_msgs.msg import String
from LOBOROBOT import LOBOROBOT
import RPi.GPIO as GPIO

class RobotController:
    def __init__(self):
        self.clbrobot = LOBOROBOT()
        rospy.init_node('robot_controller', anonymous=True)
        rospy.Subscriber('robot_commands', String, self.command_callback)
    
    def command_callback(self, msg):
        command = msg.data
        if command == "forward":
            self.clbrobot.t_up(50, 3)
        elif command == "backward":
            self.clbrobot.t_down(50, 3)
        elif command == "left":
            self.clbrobot.turnLeft(50, 3)
        elif command == "right":
            self.clbrobot.turnRight(50, 3)
        elif command == "stop":
            self.clbrobot.t_stop(0)
        # 其他命令可以继续添加

    def run(self):
        try:
            rospy.spin()
        except KeyboardInterrupt:
            self.clbrobot.t_stop(0)
            GPIO.cleanup()

if __name__ == "__main__":
    controller = RobotController()
    controller.run()
