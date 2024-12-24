import random
import string
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from typing import *
from src.process.process import ProcessState
from src.process.wrapped_process import WrappedProcess


def random_process_name(length=4):
    sample = random.sample(string.ascii_letters + string.digits, 62)
    return ''.join([random.choice(sample) for _ in range(length)])


def generate_random_processes(
        n_processes: int = 20, lens_mean_normal: int = 30, lens_std_normal: int = 10, density: float = 5.0,
):
    """
    :param n_processes: amount of processes
    :param lens_mean_normal: mean of processes
    :param lens_std_normal: std of processes
        assume process_length ~ |N(mean, std)|
    :param density: ≈ cpu_times_needed / time_range of job flow.
        num of jobs N, at timestep t ~ Poisson(num_processes / time_range)
    :return: Dict
    """
    MIN_PRIO, MAX_PRIO = 1, 9
    time_range = int((n_processes * lens_mean_normal) / density)
    num_processes_in_timestep = np.random.poisson(lam=n_processes / time_range, size=(time_range,))
    start_time = []
    for i, n in enumerate(num_processes_in_timestep):
        start_time += [i] * n
    lens = np.abs(np.random.normal(lens_mean_normal, lens_std_normal, size=(n_processes,))).astype(np.int32) + 1
    prio = np.random.choice(np.arange(MIN_PRIO, MAX_PRIO), size=n_processes)
    processes = [
        (t,{
            'CPU_TIME_NEEDED_TOTAL': l.item(),
            'name': random_process_name(),
            'STATIC_PRIO': p,
         },) for t, l, p in zip(start_time, lens, prio)
    ]
    return sorted(processes, key=lambda x: x[0])


def visualize_process_schedule(processes_done: Dict[int, WrappedProcess], show_order='done', top_down=True) -> None:
    """
    :param processes_done: dict, pid: WrappedTask
    :param show_order: 'done' - the moment jobs done. 'arrive' - the moment jobs arrived.
    :param top_down: the processes are top-down ordered or down-top.
    :return: None
    """
    if show_order == 'done':
        op = reversed if top_down else (lambda x: x)
    elif show_order == 'arrive':
        op = (lambda x: sorted(x, key=lambda v: v['pid'], reverse=top_down))
    else:
        raise ValueError(f'Show_order: {show_order} should be `done` or `arrive`')

    STATE_COLORS = {
        ProcessState.CREATE: "blue",
        ProcessState.START_RUNNING: "green",
        ProcessState.RUNNING: "orange",
        ProcessState.PAUSE_RUNNING: "red",
        ProcessState.FINISHED: "gray",
    }

    processes_done = [
        {'name': f'Process {p.task_base.name + "(user)" if p.task_base.is_user_task else p.task_base.name} - '
                 f'S_PRIO={p.task_base.STATIC_PRIO}',
         'pid': p.task_base.pid,
         'timeline': p.timeline,
        } for _, p in processes_done.items()
    ]

    fig, ax = plt.subplots(figsize=(10, len(processes_done)))

    for i, process in enumerate(op(processes_done)):
        timeline = process["timeline"]

        skip_next = False
        for j in range(len(timeline) - 1):
            if skip_next:
                skip_next = False
                continue

            start_time, state = timeline[j]
            end_time = timeline[j + 1][0]

            # in simulation implementation, state CREATE and START_RUNNING are in the same timestep.
            # we let CREATE 1 step earlier in visualization.
            if state is ProcessState.CREATE:
                start_time = start_time - 1
            # also, start_running and running can be in the same timestep. skip running in visualization.
            elif state is ProcessState.START_RUNNING:
                end_time = end_time + 1
                skip_next = True

            ax.barh(i, width=end_time - start_time, left=start_time, color=STATE_COLORS[state], edgecolor="black")

        # add final state
        if len(timeline) > 1:
            end_time = timeline[-1][0]
            ax.barh(i, width=1, left=end_time, color=STATE_COLORS[timeline[-1][1]], edgecolor="black")

    ax.set_yticks(range(len(processes_done)))
    ax.set_yticklabels([p["name"] for p in op(processes_done)])
    ax.set_xlabel("Time")
    ax.set_title("Process Scheduling Visualization")

    legend_handles = [mpatches.Patch(color=color, label=state.value) for state, color in STATE_COLORS.items()]
    ax.legend(handles=legend_handles, title="Process States", loc="upper right")

    plt.tight_layout()
    plt.grid(axis='x', linestyle='--', color='black')
    plt.show()