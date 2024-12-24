from typing import *
from colorcet import OrderedDict
from src.process.process import ProcessBase
from src.process.process import ProcessState as PSt


class VirtualEnv:

    def __init__(self, scheduler, n_threads=1):
        self.processes = OrderedDict()
        self.processes_done = OrderedDict()
        self.on_running = list()
        self.scheduler = scheduler
        self.timesteps = 0
        self.n_threads = n_threads

    def add_new_process(
            self,
            CPU_TIME_NEEDED_TOTAL: int,
            name: str = None,
            is_user_task: bool = False,
            STATIC_PRIO=4,
            **kwargs,
    ):
        def alloc_pid() -> int:
            return len(self.processes) + len(self.processes_done)

        pid = alloc_pid()
        new_process = ProcessBase(
            pid=pid,
            name=name,
            is_user_task=is_user_task,
            CPU_TIME_NEEDED_TOTAL=CPU_TIME_NEEDED_TOTAL,
            STATIC_PRIO=STATIC_PRIO
        )
        self.processes[pid] = self.scheduler.wrap_task(new_process)
        self.processes[pid].timeline.append((self.timesteps, PSt.CREATE))

    def tick(self):
        self.scheduler.schedule(self)

        finished_process_pids = []
        for pid in self.on_running:
            self.processes[pid].CPU_TIME_NEEDED -= 1
            self.processes[pid].timeline.append((self.timesteps, PSt.RUNNING))
            if self.processes[pid].CPU_TIME_NEEDED <= 0:
                process = self.processes.pop(pid)
                process.timeline.append((self.timesteps + 1, PSt.FINISHED))
                self.processes_done[pid] = process

                finished_process_pids.append(pid)

        for pid in finished_process_pids:
            self.on_running.remove(pid)

        self.timesteps += 1