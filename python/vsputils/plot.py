import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def plot_load(load: pd.DataFrame,
              ax: plt.Axes,
              vs: list[int] | int | None = None,
              dtype: str = 'cl',
              chord_dist: bool = False,
              c_ref: float = 1.0) -> list[Line2D]:

    if vs is None:
        ldf = load
    else:
        try:
            ldf = load[load['VortexSheet'].isin(vs)]
        except TypeError:
            ldf = load[load['VortexSheet'] == vs]

    dist_type = {'cl': 'cl*c/cref',
                 'cd': 'cdi*c/cref',
                 'cm': 'cmyi*c/cref'}
    dist_name = dist_type.get(dtype, dtype)

    lns = []
    for a, df in ldf.groupby('aoa'):
        if chord_dist:
            l, = ax.plot(df['Yavg'], df[dist_name] / df['Chord'] * c_ref, label=a)  # noqa: E501
        else:
            l, = ax.plot(df['Yavg'], df[dist_name], label=a)
        lns.append(l)

    return lns
