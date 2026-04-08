# -*- coding: utf-8 -*-
"""Print utilities for biovector."""
from tabulate import tabulate
import datetime


def print_summary(df):
    """Print a summary of a workout dataframe."""
    startingtime = datetime.datetime.fromtimestamp(df['Timestamp'].values[0])
    name = df['Workout Name'].values[0]
    number = df['Number'].values[0]
    program = df['Program'].values[0]
    start = str(df['Time'].values[0])
    duration = str(datetime.datetime.now() - startingtime)[:-7]
    Phi = int(sum(list(df['phi'])))
    H = round(sum(list(df['h'])), 1)
    print('*' * 70, '\n')
    print(f"{name:^20}\n{number:^20}\n{program:^20}\n{start:^20}\n{duration:^20}\n{str(Phi) + ' kg-m':^20}\n{str(H) + ' hard sets':^20}")
    print('{:^20}{:<7}{:<3} {:<4} {:<4}  {:<4} {:<5} {:<2}'.format('', 'W', 'R', '1RM', 'Best', '1RL', 'I', 'h'))
    for i in df.index:
        exo = df.loc[i, 'Exercise Name']
        reps = df.loc[i, 'Reps']
        weight = df.loc[i, 'Weight']
        rm = df.loc[i, '1RM']
        predrm = df.loc[i, 'Pred1RM']
        predrl = df.loc[i, 'Pred1RL']
        its = df.loc[i, 'Int']
        h = df.loc[i, 'h']
        print(f"{exo:^20}{int(weight):<7}{int(reps):<3} {int(predrm):<4} {int(rm):<4}  {int(predrl):<4} {its:<4.0%} {h:<2}")
    print('*' * 70)


if __name__ == '__main__':
    from . import bv_utils
    sets = bv_utils.Biovector(selected=['sets']).sets
    workout = sets[sets['Number'] == 1000]
    print_summary(workout)
