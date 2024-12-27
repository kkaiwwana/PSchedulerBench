from src.run.virtual_env import VirtualEnv
from src.process.process import ProcessBase
from src.process.wrapped_process import WrappedProcess
from src.process.process import ProcessState as PSt


class SchedulerBase:
    def __init__(self,*args, **kwargs):
        self.schedule_times = 0

    def reset(self):
        self.schedule_times = 0

    def __str__(self):
        return self.__class__.__name__

    def wrap_task(self, task: ProcessBase) -> WrappedProcess:
        return WrappedProcess(task)

    def schedule(self, env: VirtualEnv) -> None:
        raise NotImplementedError


class FCFS(SchedulerBase):
    """First-Come, First-Served"""
    def schedule(self, env: VirtualEnv) -> None:
        if len(env.on_running) == env.n_threads:
            return

        for pid in sorted(env.processes.keys())[:env.n_threads]:
            # first came job has smalled pid.
            if pid not in env.on_running and len(env.on_running) < env.n_threads:
                env.on_running.append(pid)
                env.processes[pid].timeline.append((env.timesteps, PSt.START_RUNNING))

                self.schedule_times += 1


class SJF(SchedulerBase):
    """Shortest-Job-First, SJF"""
    def __init__(self, is_preemptive=False):
        super().__init__()
        self.is_preemptive = is_preemptive

    def __str__(self):
        return 'SJF' if not self.is_preemptive else 'SJG_Preemptive'

    def schedule(self, env: VirtualEnv) -> None:

        for pid, _ in sorted(env.processes.items(), key=lambda kv: kv[-1].CPU_TIME_NEEDED)[:env.n_threads]:
            # first came job has smalled pid.
            if len(env.on_running) < env.n_threads:
                if pid not in env.on_running:
                    env.on_running.append(pid)
                    env.processes[pid].timeline.append((env.timesteps, PSt.START_RUNNING))

                    self.schedule_times += 1

            elif self.is_preemptive:
                if pid not in env.on_running:
                    pid_to_pause = max(env.on_running, key=lambda x: env.processes[x].CPU_TIME_NEEDED)
                    env.on_running.remove(pid_to_pause)
                    env.processes[pid_to_pause].timeline.append((env.timesteps, PSt.PAUSE_RUNNING))

                    env.on_running.append(pid)
                    env.processes[pid].timeline.append((env.timesteps, PSt.START_RUNNING))

                    self.schedule_times += 1


class HRRF(SchedulerBase):
    """Highest Response Ratio First"""
    def schedule(self, env: VirtualEnv) -> None:
        if len(env.on_running) == env.n_threads:
            return

        def response_ratio(kv):
            return (env.timesteps - kv[-1].get_state_timesteps(PSt.CREATE)[0]) / kv[-1].CPU_TIME_NEEDED

        for pid, _ in sorted(env.processes.items(), key=lambda kv: response_ratio(kv), reverse=True)[:env.n_threads]:
            if pid not in env.on_running and len(env.on_running) < env.n_threads:
                env.on_running.append(pid)
                env.processes[pid].timeline.append((env.timesteps, PSt.START_RUNNING))

                self.schedule_times += 1


class RR(SchedulerBase):
    """Round-Robin"""
    def __init__(self, time_slice=5, **kwargs):
        super().__init__()
        self.time_slice = time_slice

    def wrap_task(self, task: ProcessBase) -> WrappedProcess:
        return WrappedProcess(task, slice_cnt=0)

    def schedule(self, env: VirtualEnv) -> None:
        pid_to_pause = []
        for pid in env.on_running:
            if env.processes[pid].slice_cnt == 0:
                pid_to_pause.append(pid)

        for pid in pid_to_pause:
            env.on_running.remove(pid)
            env.processes[pid].timeline.append((env.timesteps, PSt.PAUSE_RUNNING))
            env.processes.move_to_end(pid)

        if len(env.on_running) < env.n_threads:
            for pid in list(env.processes.keys())[:env.n_threads]:
                if pid not in env.on_running and len(env.on_running) < env.n_threads:
                    env.on_running.append(pid)
                    env.processes[pid].timeline.append((env.timesteps, PSt.START_RUNNING))
                    env.processes[pid].slice_cnt = self.time_slice

                    self.schedule_times += 1

        for pid in env.on_running:
            env.processes[pid].slice_cnt -= 1


class SP(SchedulerBase):
    """Static Priority or MQ"""
    def __init__(self, min_time_slice=1, time_slice_increment=1, **kwargs):
        super().__init__()
        self.min_time_slice = min_time_slice
        self.time_slice_increment = time_slice_increment

    def wrap_task(self, task: ProcessBase) -> WrappedProcess:
        return WrappedProcess(task, slice_cnt=0, d_prio=task.STATIC_PRIO)

    def schedule(self, env: VirtualEnv) -> None:
        pid_to_pause = []
        for pid in env.on_running:
            if env.processes[pid].slice_cnt == 0:
                pid_to_pause.append(pid)

        for pid in pid_to_pause:
            env.on_running.remove(pid)
            env.processes[pid].timeline.append((env.timesteps, PSt.PAUSE_RUNNING))
            env.processes.move_to_end(pid)

        if len(env.on_running) < env.n_threads:

            for pid, process in sorted(
                    env.processes.items(), key=lambda kv: kv[-1].task_base.STATIC_PRIO, reverse=True)[:env.n_threads]:
                if pid not in env.on_running and len(env.on_running) < env.n_threads:
                    env.on_running.append(pid)
                    env.processes[pid].timeline.append((env.timesteps, PSt.START_RUNNING))
                    time_slices = self.min_time_slice + process.task_base.STATIC_PRIO * self.time_slice_increment
                    env.processes[pid].slice_cnt = time_slices

                    self.schedule_times += 1

        for pid in env.on_running:
            env.processes[pid].slice_cnt -= 1


class DP(SchedulerBase):
    """Dynamic Priority"""
    def __init__(self, min_time_slice=1, time_slice_increment=1, **kwargs):
        super().__init__()
        self.min_time_slice = min_time_slice
        self.time_slice_increment = time_slice_increment

    def wrap_task(self, task: ProcessBase) -> WrappedProcess:
        return WrappedProcess(task, slice_cnt=0, d_prio=task.STATIC_PRIO)

    def schedule(self, env: VirtualEnv) -> None:
        pid_to_pause = []
        for pid in env.on_running:
            if env.processes[pid].slice_cnt == 0:
                pid_to_pause.append(pid)

        for pid in pid_to_pause:
            env.on_running.remove(pid)
            env.processes[pid].timeline.append((env.timesteps, PSt.PAUSE_RUNNING))

        if len(env.on_running) < env.n_threads:
            # update dynamic priority
            for pid, process in env.processes.items():
                total_time = (env.timesteps - process.get_state_timesteps(PSt.CREATE)[0]) + 1
                run_time = len(process.get_state_timesteps(PSt.RUNNING)) / total_time
                wait_time = 1 - run_time
                env.processes[pid].d_prio = process.task_base.STATIC_PRIO - run_time + wait_time

            for pid, process in sorted(env.processes.items(), key=lambda kv: kv[-1].d_prio, reverse=True)[:env.n_threads]:
                if pid not in env.on_running and len(env.on_running) < env.n_threads:
                    env.on_running.append(pid)
                    env.processes[pid].timeline.append((env.timesteps, PSt.START_RUNNING))
                    time_slices = self.min_time_slice + process.task_base.STATIC_PRIO * self.time_slice_increment
                    env.processes[pid].slice_cnt = time_slices

                    self.schedule_times += 1

        for pid in env.on_running:
            env.processes[pid].slice_cnt -= 1


class DPMQ(SchedulerBase):
    """Dynamic Priority Multi-level Queue"""
    def __init__(self, min_time_slice=1, time_slice_increment=1, **kwargs):
        super().__init__()
        self.min_time_slice = min_time_slice
        self.time_slice_increment = time_slice_increment

    def wrap_task(self, task: ProcessBase) -> WrappedProcess:
        return WrappedProcess(task, slice_cnt=0, d_prio=task.STATIC_PRIO)

    def schedule(self, env: VirtualEnv) -> None:
        pid_to_pause = []
        for pid in env.on_running:
            if env.processes[pid].slice_cnt == 0:
                pid_to_pause.append(pid)

        for pid in pid_to_pause:
            env.on_running.remove(pid)
            env.processes[pid].timeline.append((env.timesteps, PSt.PAUSE_RUNNING))

        if len(env.on_running) < env.n_threads:
            # update dynamic priority
            for pid, process in env.processes.items():
                total_time = (env.timesteps - process.get_state_timesteps(PSt.CREATE)[0]) + 1
                run_time = len(process.get_state_timesteps(PSt.RUNNING)) / total_time
                wait_time = 1 - run_time
                env.processes[pid].d_prio = process.task_base.STATIC_PRIO - run_time + wait_time

            def first_queue_not_empty(kv):
                # sort by keywords: [STATIC_PRIO, D_PRIO]
                return kv[-1].task_base.STATIC_PRIO, kv[-1].d_prio

            for pid, process in sorted(env.processes.items(), key=first_queue_not_empty, reverse=True)[:env.n_threads]:
                if pid not in env.on_running and len(env.on_running) < env.n_threads:
                    env.on_running.append(pid)
                    env.processes[pid].timeline.append((env.timesteps, PSt.START_RUNNING))
                    time_slices = self.min_time_slice + process.task_base.STATIC_PRIO * self.time_slice_increment
                    env.processes[pid].slice_cnt = time_slices

                    self.schedule_times += 1

        for pid in env.on_running:
            env.processes[pid].slice_cnt -= 1


class MFQ(SchedulerBase):
    """Multi-level Feedback Queue"""
    def __init__(self, base_time_slices=2, n_queues=8):
        super().__init__()
        self.base_time_slices=base_time_slices
        self.n_queses = n_queues

    def wrap_task(self, task: ProcessBase) -> WrappedProcess:
        return WrappedProcess(task, queue_index=0, slice_cnt=0)

    def schedule(self, env: VirtualEnv) -> None:
        pid_to_pause = []
        for pid in env.on_running:
            if env.processes[pid].slice_cnt == 0:
                pid_to_pause.append(pid)

        for pid, process in sorted(env.processes.items(), key=lambda kv: kv[-1].queue_index)[:env.n_threads]:
            if pid not in env.on_running:
                if env.on_running == env.n_threads:
                    max_queue_pid = max(env.on_running, key=lambda x: env.processes[x].queue_index)
                    if env.processes[max_queue_pid].queue_index > env.processes[pid]:
                        pid_to_pause.append(max_queue_pid)

                        env.on_running.append(pid)
                        env.processes[pid].timeline.append((env.timesteps, PSt.START_RUNNING))
                        env.processes[pid].slice_cnt = self.base_time_slices * 2 ** process.queue_index

                        self.schedule_times += 1

                else:
                    env.on_running.append(pid)
                    env.processes[pid].timeline.append((env.timesteps, PSt.START_RUNNING))
                    env.processes[pid].slice_cnt = self.base_time_slices * 2 ** process.queue_index

                    self.schedule_times += 1

        for pid in set(pid_to_pause):
            env.on_running.remove(pid)
            env.processes[pid].timeline.append((env.timesteps, PSt.PAUSE_RUNNING))
            env.processes[pid].slice_cnt = 0
            env.processes[pid].queue_index = min(self.n_queses, env.processes[pid].queue_index + 1)
            env.processes.move_to_end(pid)

        for pid in env.on_running:
            env.processes[pid].slice_cnt -= 1


class SPMFQ(SchedulerBase):
    """
    Static Priority Multi-level Feedback Queue
    time_slices[i + 1] = time_slices[i] *
    """
    def __init__(self, base_time_slices=2, min_exp=1.1, exp_increment=0.15, n_queues=16):
        super().__init__()
        self.base_time_slices = base_time_slices
        self.min_exp = min_exp
        self.exp_increment = exp_increment
        self.n_queses = n_queues

    def wrap_task(self, task: ProcessBase) -> WrappedProcess:
        return WrappedProcess(task, queue_index=0, slice_cnt=0)

    def schedule(self, env: VirtualEnv) -> None:
        pid_to_pause = []
        for pid in env.on_running:
            if env.processes[pid].slice_cnt == 0:
                pid_to_pause.append(pid)

        for pid, process in sorted(env.processes.items(), key=lambda kv: kv[-1].queue_index)[:env.n_threads]:
            if pid not in env.on_running:
                if env.on_running == env.n_threads:
                    max_queue_pid = max(env.on_running, key=lambda x: env.processes[x].queue_index)
                    if env.processes[max_queue_pid].queue_index > env.processes[pid]:
                        pid_to_pause.append(max_queue_pid)

                        env.on_running.append(pid)
                        env.processes[pid].timeline.append((env.timesteps, PSt.START_RUNNING))
                        exp_val = (self.min_exp +
                                   self.exp_increment * process.task_base.STATIC_PRIO) ** process.queue_index
                        env.processes[pid].slice_cnt = int(self.base_time_slices * exp_val)

                        self.schedule_times += 1

                else:
                    env.on_running.append(pid)
                    env.processes[pid].timeline.append((env.timesteps, PSt.START_RUNNING))
                    exp_val = (self.min_exp +
                               self.exp_increment * process.task_base.STATIC_PRIO) ** process.queue_index
                    env.processes[pid].slice_cnt = int(self.base_time_slices * exp_val)

                    self.schedule_times += 1

        for pid in set(pid_to_pause):
            env.on_running.remove(pid)
            env.processes[pid].timeline.append((env.timesteps, PSt.PAUSE_RUNNING))
            env.processes[pid].slice_cnt = 0
            env.processes[pid].queue_index = min(self.n_queses, env.processes[pid].queue_index + 1)
            env.processes.move_to_end(pid)

        for pid in env.on_running:
            env.processes[pid].slice_cnt -= 1


class MPMFQ(SchedulerBase):
    """
    Mixed (Static+Dynamic) Priority Multi-level Feedback Queue
    """
    def __init__(self, base_time_slices=2, min_exp=1.1, exp_increment=0.15, n_queues=16):
        super().__init__()
        self.base_time_slices = base_time_slices
        self.min_exp = min_exp
        self.exp_increment = exp_increment
        self.n_queses = n_queues

    def wrap_task(self, task: ProcessBase) -> WrappedProcess:
        return WrappedProcess(task, queue_index=0, slice_cnt=0, d_prio=task.STATIC_PRIO)

    def schedule(self, env: VirtualEnv) -> None:
        pid_to_pause = []
        for pid in env.on_running:
            if env.processes[pid].slice_cnt == 0:
                pid_to_pause.append(pid)

        for pid, process in env.processes.items():
            total_time = (env.timesteps - process.get_state_timesteps(PSt.CREATE)[0]) + 1
            run_time = len(process.get_state_timesteps(PSt.RUNNING)) / total_time
            wait_time = 1 - run_time
            env.processes[pid].d_prio = process.task_base.STATIC_PRIO - run_time + wait_time

        for pid, process in sorted(env.processes.items(), key=lambda kv: (kv[-1].queue_index, -kv[-1].d_prio))[:env.n_threads]:
            if pid not in env.on_running:
                if env.on_running == env.n_threads:
                    max_queue_pid = max(env.on_running, key=lambda x: env.processes[x].queue_index)
                    if env.processes[max_queue_pid].queue_index > env.processes[pid]:
                        pid_to_pause.append(max_queue_pid)

                        env.on_running.append(pid)
                        env.processes[pid].timeline.append((env.timesteps, PSt.START_RUNNING))
                        exp_val = (self.min_exp +
                                   self.exp_increment * process.task_base.STATIC_PRIO) ** process.queue_index
                        env.processes[pid].slice_cnt = int(self.base_time_slices * exp_val)

                        self.schedule_times += 1

                else:
                    env.on_running.append(pid)
                    env.processes[pid].timeline.append((env.timesteps, PSt.START_RUNNING))
                    exp_val = (self.min_exp +
                               self.exp_increment * process.task_base.STATIC_PRIO) ** process.queue_index
                    env.processes[pid].slice_cnt = int(self.base_time_slices * exp_val)

                    self.schedule_times += 1

        for pid in set(pid_to_pause):
            env.on_running.remove(pid)
            env.processes[pid].timeline.append((env.timesteps, PSt.PAUSE_RUNNING))
            env.processes[pid].slice_cnt = 0
            env.processes[pid].queue_index = min(self.n_queses, env.processes[pid].queue_index + 1)
            env.processes.move_to_end(pid)

        for pid in env.on_running:
            env.processes[pid].slice_cnt -= 1