import sys
import hydra
import numpy as np
import itertools
import copy
import random
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt

from hydra.utils import instantiate, call
from omegaconf import DictConfig
from pathlib import Path
from typing import *
from colorcet import OrderedDict

CONFIG_PATH = str(Path.cwd() / 'config')
CONFIG_NAME = 'main'


def get_params_group(val_range: int or List, n_groups=1, is_integer=True, is_geometric=False):

    def arithmetic_seq(start, end, num_elements):
        seq = np.linspace(start, end, num_elements)
        return list(seq) if not is_integer else list(seq.astype(np.int32))

    def geometric_seq(start, end, num_elements):
        r = (end / start) ** (1 / (num_elements - 1))
        return [start * (r ** i) if not is_integer else int(start * (r ** i)) for i in range(num_elements)]

    if isinstance(val_range, int):
        return [val_range]
    elif len(val_range) == 1 or n_groups == 1:
        return [val_range[0]]
    else:
        return geometric_seq(*val_range, n_groups) if is_geometric else arithmetic_seq(*val_range, n_groups)


def generate_test_groups(
        n_processes_group,
        lens_mean_normal_group,
        lens_std_normal_group,
        density_group,
):
    params_group = OrderedDict(
        n_processes=n_processes_group,
        lens_mean_normal=lens_mean_normal_group,
        lens_std_normal=lens_std_normal_group,
        density=density_group
    )
    variable_groups = {k: [] for k in params_group.keys()}

    for name, group in params_group.items():
        groups_remain = copy.copy(params_group)
        groups_remain.pop(name)
        keys = list(groups_remain.keys())
        for a, b, c in itertools.product(*[g for g in groups_remain.values()]):
            variable_groups[name].append(({keys[0]: a, keys[1]: b, keys[2]: c}, group))

    return variable_groups


def plot(metrics_result, var_name, var, path):
    x = range(len(var)) # The varying parameter, e.g., task counts
    algorithms = metrics_result.keys()
    metrics = {
        'PRIO_TAT & TAT': ['prio_TAT', 'TAT'],
        'PRIO_RT & RT': ['prio_RT', 'RT'],
        'PRIO_TAT_NORM & TAT_NORM': ['prio_TAT_Norm', 'TAT_Norm'],
        'PRIO_RT_NORM & RT_NORM': ['prio_RT_Norm', 'RT_Norm'],
        'SCHEDULE_TIMES': ['schedule_times']
    }
    # Plot
    fig, axes = plt.subplots(3, 2, figsize=(15, 18))
    axes = axes.flatten()

    colors_to_use = random.sample(list(mcolors.TABLEAU_COLORS.keys()), len(algorithms))

    for idx, (metric_name, metric_keys) in enumerate(metrics.items()):
        ax = axes[idx]
        for i, algo in enumerate(algorithms):
            values = metrics_result[algo]
            if len(metric_keys) == 2:  # For dual metrics
                y1 = [v[metric_keys[0]] for v in values]
                y2 = [v[metric_keys[1]] for v in values]

                ax.plot(x, y1, label=f'{algo} - {metric_keys[0]}', marker='o', color=colors_to_use[i])
                ax.plot(x, y2, label=f'{algo} - {metric_keys[1]}', linestyle='--', marker='x', color=colors_to_use[i])
            else:  # Single metric
                y = [v[metric_keys[0]] for v in values]
                ax.plot(x, y, label=f'{algo} - {metric_keys[0]}', marker='o', color=colors_to_use[i])

        ax.set_title(metric_name.replace('_', ' '))
        ax.set_xlabel(var_name)
        ax.set_xticks(x)
        ax.set_xticklabels([str(v) for v in var])
        ax.set_ylabel("Value")
        ax.legend()

        ax.grid()

    # Remove unused subplot
    for i in range(len(metrics), len(axes)):
        fig.delaxes(axes[i])

    plt.tight_layout()
    plt.savefig(path)


@hydra.main(version_base=None, config_path=CONFIG_PATH, config_name=CONFIG_NAME)
def main(cfg: DictConfig):
    log_path = Path(cfg.exp.save_dir).joinpath(cfg.exp.uuid)
    Path(log_path).mkdir(exist_ok=True, parents=False)

    test_groups = call(cfg.test_groups)

    for variable_param_name, params in test_groups.items():
        for fixed_param, variable_param in params:
            if len(variable_param) == 1 and cfg.exp.skip_single_var:
                continue

            fixed_param_to_str = ''.join([f'{k}={v},' for k, v in fixed_param.items()])
            metrics_result = OrderedDict({k: [] for k in cfg.schedulers.keys()})
            for scheduler_name, scheduler in instantiate(cfg.schedulers).items():
                for p in variable_param:
                    metrics = []
                    for _ in range(cfg.exp.n_repeats):
                        scheduler.reset()
                        test_processes = generate_random_processes(**(fixed_param | {variable_param_name: p}))
                        _, metric = benchmark_single(
                            scheduler=scheduler,
                            test_processes=test_processes,
                            verbose=False,
                            n_threads=cfg.virtual_env.n_threads
                        )
                        metrics.append(metric)

                    metric_mean = {k: sum([metric[k] for metric in metrics]) / cfg.exp.n_repeats for k in metrics[0].keys()}
                    metrics_result[scheduler_name].append(metric_mean)

            save_path = Path(log_path).joinpath(variable_param_name)
            save_path.mkdir(exist_ok=True, parents=False)
            plot(metrics_result, variable_param_name, variable_param, path=save_path / fixed_param_to_str.__add__('.png'))


if __name__ == '__main__':
    sys.path.append('./')
    from src.run.benchmark import benchmark_single
    from src.schedulers.schedulers import *
    from src.utils.utils import generate_random_processes

    main()

