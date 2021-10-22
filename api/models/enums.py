from enum import Enum


class Device(str, Enum):
    mill = "mill"
    lathe = "lathe"
    gom = "gom"
    robot = "robot"


class DeviceAuto(str, Enum):
    auto = "auto"
    mill = "mill"
    lathe = "lathe"
    gom = "gom"
    robot = "robot"
