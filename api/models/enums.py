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


class UserStatusEnum(str, Enum):
    active = "active"
    inactive = "inactive"
    archive = "archive"


class ProjectStatusEnum(str, Enum):
    active = "active"
    archive = "archive"


class ProjectVersionStatusEnum(str, Enum):
    edit = "edit"
    final = "final"
    deleted = "deleted"
    archive = "archive"


class InstallationStatusEnum(str, Enum):
    todo = "todo"
    working = "working"
    done = "done"
    fail = "fail"
