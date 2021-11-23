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


class AlarmCondEventRel(str, Enum):
    eq = "="
    neq = "!="
    contains = "*"
    not_contains = "!*"


class CommonStatusEnum(str, Enum):
    active = "active"
    inactive = "inactive"


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


class FileProtocolEnum(str, Enum):
    git = "git"
    unc = "unc"
    int = "int"


class WorkpieceStatusEnum(str, Enum):
    good = "good"
    bad = "bad"
    inprogress = "inprogress"
    unknown = "unknown"
