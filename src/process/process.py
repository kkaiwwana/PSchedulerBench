from typing import *
from enum import Enum


class ProcessState(Enum):
    CREATE = "CREATE"
    START_RUNNING = "START_RUNNING"
    RUNNING = "RUNNING"
    PAUSE_RUNNING = "PAUSE_RUNNING"
    FINISHED = "FINISHED"


class ProcessBase:
    def __init__(
        self,
        pid: int,
        CPU_TIME_NEEDED_TOTAL: int,
        name: str = None,
        is_user_task: bool = False,
        STATIC_PRIO=4
    ):
        self.pid = pid
        self.CPU_TIME_NEEDED_TOTAL = CPU_TIME_NEEDED_TOTAL  # invisible to schedulers
        self.name = name if name else 'EMPTY_NAME'
        self.is_user_task = is_user_task
        self.STATIC_PRIO=STATIC_PRIO