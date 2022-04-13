# -*- coding: utf-8 -*-
"""
Created on Wed Apr 13 13:15:40 2022

@author: mceau
"""
from tabulate import tabulate
import datetime
import pandas as pd, numpy as np

# weights = pd.read_csv('../data/measures/weight.csv')
sets = pd.read_csv('../data/sets.csv')
# exercises = pd.read_csv('../data/exercises.csv')

workout = sets[sets['Number'] == 1000]
# wex = set(workout['ID'].values)
# wexn = set(workout['Exercise Name'].values)
# #wexd = {i : {k:v for k,v in zip(exercises.columns,exercises[exercises['ID']==i].to_numpy()[0])} for i in wex}
# name = workout['Workout Name'].values[0]
# number = workout['Number'].values[0]
# program = workout['Program'].values[0]
# wbe = [workout[workout['ID']==i][["Exercise Name","Weight","Reps","Pred1RL","1RL","Pred1RM","1RM","Int","h"]] for i in wex]

# print(name,number,program)
# for n,i in enumerate(wexn):
#     print(tabulate(wbe[n],headers=['W','R','pL','L','pM','M','I','h'],
#                    showindex=True,tablefmt="pretty"))

def print_summary(df):
    startingtime = datetime.datetime.fromtimestamp(df['Timestamp'].values[0])
    name = df['Workout Name'].values[0]
    number = df['Number'].values[0]
    program = df['Program'].values[0]
    start = str(df['Time'].values[0])
    duration = str(datetime.datetime.now() - startingtime)[:-7]
    Phi = int(sum(list(df['phi'])))
    H = round(sum(list(df['h'])),1)
    print('*'*70,'\n')
    print(f"{name:^20}\n{number:^20}\n{program:^20}\n{start:^20}\n{duration:^20}\n{str(Phi)+' kg-m':^20}\n{str(H)+' hard sets':^20}")
    print('{:^20}{:<7}{:<3} {:<4} {:<4}  {:<4} {:<5} {:<2}'.format('', 'W', 'R', '1RM', 'Best', '1RL', 'I', 'h'))
    for i in df.index:
        exo, reps, weight, rm, predrm, predrl, its, h = df.loc[i,'Exercise Name'], df.loc[i,'Reps'], df.loc[i,'Weight'], df.loc[i,'1RM'], df.loc[i,'Pred1RM'], df.loc[i,'Pred1RL'], df.loc[i,'Int'], df.loc[i,'h']
        print(f"{exo:^20}{int(weight):<7}{int(reps):<3} {int(predrm):<4} {int(rm):<4}  {int(predrl):<4} {its:<4.0%} {h:<2}")
    print('*'*70)

if __name__=='__main__':
    #print(workout.columns)
    print_summary(workout)
