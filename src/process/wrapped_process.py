from src.process.process import ProcessBase
from src.process.process import ProcessState as PSt
from typing import *


class WrappedProcess:

    def __init__(self, task: ProcessBase, **extra_property):
        self.task_base = task
        self.CPU_TIME_NEEDED = task.CPU_TIME_NEEDED_TOTAL
        self.timeline = list()  # log timeline of this task, e.g. begin, pause, end.

        if extra_property is not None:
            self.register_property(**extra_property)

    def register_property(self, **extra_property):
        for k, v in extra_property.items():
            setattr(self, k, v)

    def get_state_timesteps(self, query_state: PSt) -> List:
        return list(filter(
            lambda x: x is not None, [t if state is query_state else None for t, state in self.timeline]))

    def compute_metrics(self):
        assert self.timeline[-1][-1] is PSt.FINISHED
        t_created = self.get_state_timesteps(PSt.CREATE)[0]
        turnaround_t = self.get_state_timesteps(PSt.FINISHED)[0] - t_created
        weighted_turnaround_t = turnaround_t / self.task_base.CPU_TIME_NEEDED_TOTAL
        response_t = self.get_state_timesteps(PSt.START_RUNNING)[0] - t_created
        weighted_response_t = response_t / self.task_base.CPU_TIME_NEEDED_TOTAL

        return dict(
            TAT=turnaround_t,
            TAT_Norm=weighted_turnaround_t,
            RT=response_t,
            RT_Norm=weighted_response_t
        )