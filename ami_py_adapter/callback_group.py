from enum import Enum

class CallbackGroup(Enum):
    ALL_LOGS = 0,
    SOCKET_LOGS = 1,
    LOGFILE_LOGS = 2