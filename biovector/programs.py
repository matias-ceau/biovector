import pandas as pd, numpy as np
import metrics
import yaml

with open('../data/config.yaml','r') as file:
    config = yaml.safe_load(file)

#531
W531 = '531'
primary531 = ['S00','P10.0','P01.00','H00.0']
class W531:
    def __init__(self,week,movement):
        self.movement = movement
        self.week = int(week)
        with open('../data/programs/531.yaml','r') as file:
            self.config = yaml.safe_load(file)
        self.TM = config['training_max'] 

    def give_numbers(self,week,movement):
        return [self.TM[movement]*i/100 for i in self.config[movement][week-1]]

# PPL2.0
PPL2 = 'PPL 2.0'
H = ['H00.0','H01.0','H30.1'] #deadlift, romanian deadlift, zercher goodmorning
P = ['P01.00','P10.0','P20'] #bench press, military press, dips
T = ['T11.1','T00','T23.1'] #row, chin up, karwoski row
S = ['S00','S10','S31'] # squat, front squat, bulgarian split squat
primaryPPL2 = [H,P,T,S]
accessory = ['X','C','U','S','T','P','L']

# monolith
mon = 'monolith'
with open('../data/programs/monolith.yaml','r') as file:
    monolith = yaml.safe_load(file)
class Monolith:
    def __init__(self,week,L):
        self.name = L
        self.week = int(week)
        self.number = int(week)*{'A':1,'B':2,'C':3}[L]
        self.raw = {k : v[self.week-1] for k,v in monolith[L].items()}
        self.sets = metrics.import_data()[0]
        self.exercises = metrics.import_data()[1]
        self.IDex = {k:v for k,v in zip(list(self.exercises['ID']),list(self.exercises['Exercise']))}
        self.selX = [k for k,v in self.raw.items()]
        self.TM = config['training_max'] 
        self.todo = [{self.IDex[i] : [round(x/100*self.TM[i]) for x in self.raw[i]] for i in self.raw.keys() if type(self.raw[i]) == list},
                     {self.IDex[i] : self.raw[i] for i in self.raw.keys() if type(self.raw[i]) != list}]

    def __repr__(self):
        string = ''
        for i in self.raw.keys():
            if type(self.raw[i]) == list:
                string += f'{self.IDex[i]} : {[round(x/100 * self.TM[i]) for x in self.raw[i]]}\n'
            else: string += f'{self.IDex[i]} : {self.raw[i]}\n'
        return string

    def show_todo(self,summary):
        todo = {}
        for x in self.todo[1].keys():
            try: done = sum(list(summary[summary['Exercise Name'] == x]['Reps'])) 
            except KeyError: done = 0
            todo[x] = int(self.todo[1][x] - done) 
        return todo

###################################################
choice = [mon,W531,PPL2]
default = mon
