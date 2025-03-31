import os
from enum import Enum
from enum import auto


class LinuxSessionType(Enum):
    X11 = auto()
    WAYLAND = auto()
    UNKNOWN = auto()

    @classmethod
    def detect(cls) -> "LinuxSessionType":
        session_type = os.getenv("XDG_SESSION_TYPE", "").lower()

        if session_type == "x11":
            return cls.X11
        elif session_type == "wayland":
            return cls.WAYLAND
        return cls.UNKNOWN

    def __str__(self):
        return self.name.lower()
