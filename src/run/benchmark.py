from src.run.virtual_env import VirtualEnv
from src.schedulers.schedulers import SchedulerBase


def evaluate(processes_done, scheduler, verbose=True):
    """
    return following metrics:
    1. turnround_time: regular, normalized, prio-weighted
    2. response_time: regular, normalized, prio-weighted
    """
    metrics = dict()
    sum_prio = sum([task.task_base.STATIC_PRIO for _, task in processes_done.items()])
    num_processes = len(processes_done)
    for pid, processes in processes_done.items():
        for k, v in processes.compute_metrics().items():
            if k in metrics.keys():
                metrics[k].append(v / num_processes)
                metrics['prio_' + k].append(v * processes.task_base.STATIC_PRIO / sum_prio)
            else:
                metrics[k] = [v / num_processes]
                metrics['prio_' + k] = [v * processes.task_base.STATIC_PRIO / sum_prio]

    for k, v in metrics.items():
        metrics[k] = sum(v)
        if verbose:
            print(f'{k}: {sum(v):.2f}')

    metrics['schedule_times'] = scheduler.schedule_times
    if verbose:
        print(f'schedule_times: {scheduler.schedule_times}')
    return metrics


def benchmark_single(scheduler: SchedulerBase, test_processes, n_threads=2, verbose=True):
    env = VirtualEnv(scheduler, n_threads=n_threads)

    index = 0
    while True:
        while index < len(test_processes) and test_processes[index][0] == env.timesteps:
            env.add_new_process(**test_processes[index][1])
            index += 1
        if env.timesteps > test_processes[-1][0] and env.processes == {}:
            break

        env.tick()

    print(f'Scheduler:{scheduler}, {len(env.processes_done)} jobs have done.')
    metrics = evaluate(processes_done=env.processes_done, scheduler=scheduler, verbose=verbose)
    return env.processes_done, metrics