import os, sys, numpy as np, pandas as pd, datetime
import stats, bv_utils, printbv
from bv_utils import Biovector


#######################################################################################

class Exercise(Biovector):
    def __init__(self,ID):
        super().__init__(droplist=['weight','workouts'])
        self.ID = ID
        self.exercise_history = self.sets[self.sets['ID'] == ID] #set history
        self.exercise_data = self.exercises[self.exercises['ID'] == ID] #exercise data
        self.name = list(self.exercise_data['Exercise'])[0]
        self.Delta = list(self.exercise_data['Delta'])[0]
        self.kappa = list(self.exercise_data['rho'])[0] * list(self.exercise_data['theta'])[0]
        self.Short = list(self.exercise_data['Short'])[0]
        self.est1RM = max(list(self.exercise_history['Pred1RM'])+[0])
        self.est1RL = max(list(self.exercise_history['Pred1RL'])+[0])

#######################################################################################

class Workout(Biovector):
    def __init__(self,name,program=None,t=0):
        super().__init__()
        self.name = name
        if program in 'c': self.program = 'à changer'
        if program == 'w': self.program = 'workout'
        if program == 'f': self.program = 'free'
        if self.program == 'fileadd':
            self.startingtime == t
        else:
            self.startingtime = datetime.datetime.now()
        self.start = self.startingtime.strftime("%Y-%m-%d %H:%M:%S")
        self.summary = pd.DataFrame({i:[] for i in list(self.sets.columns)})
        self.BW = self.weight.loc[len(self.weight)-1,'Weight']
        if self.program == 'free':
            self.number = 0
        else:
            self.number = int(max(list(self.sets.loc[:,'Number'])) + 1)
        self.exercise = None
        self.weight = None
        self.status = 'active'
        self.template = None

    def take_input(self, user_input):
        exercise, weight, reps, note, status = bv_utils.translate(user_input)
        if status: self.status = status #if status='end' it quits
        #possibilities
        if self.status == 'active':
            copy = self.exercise
            if exercise: self.choose_exercise(exercise)
            if self.exercise != copy: self.weight = None
            if weight or weight==0: self.weight = float(weight)
            if self.weight == None: self.weight = 0
            if reps and self.exercise and (self.weight or self.weight == 0):
                self.add_set(self.weight,int(reps),note)
            self.print_summary()
        if self.status == 'help':
            bv_utils.list_exercises(note)
        if self.status == 'delete':
            self.delete_set(note) ; self.status == None
        if self.status == 'template':
            try: self.program_print(note[0],note[1])
            except: pass
            try: self.program_print(self.week,self.L)
            except: pass
        if self.status == 'todo':
            print(self.template.show_todo(self.summary))
        if self.status == 'redo':
            self.redo(note)
            self.print_summary()

    def save(self,strg):
        if strg != 'n':
            self.export('sets')
            # bv_utils.export_data(S=self.sets)
        if self.number != 0:
            df = pd.DataFrame({'Number':    [self.number],
                               'Timestamp': [self.startingtime.timestamp()],
                               'Date':      [self.startingtime],
                               'Hardsets':  [sum(list(self.summary.loc[:,'h']))],
                               'Load':      [sum(list(self.summary.loc[:,'Load']))],
                               'Hardload':  [sum(list(self.summary.loc[:,'phi']))]})
            self.workouts = pd.concat((self.workouts,df),ignore_index=True)
            # bv_utils.export_data(K=self.workouts)
            self.export('workouts')

    def delete_set(self,n=1):
        try: n = int(n)
        except: n = 1
        if len(self.summary) < n:
            print("You're trying to delete previous sets!\n")
        else:
            self.sets = self.sets.iloc[:-n,:]
            self.summary = self.summary.iloc[:-n,:]
            self.exercise = Exercise(self.exercise.ID)

    def print_summary(self):
        printbv.print_summary(self.summary)

    def choose_exercise(self,name):
        if name in list(self.exercises['ID']):
            self.exercise = Exercise(name)
        if name in list(self.exercises['Short']):
            index = self.exercises[self.exercises['Short'] == name].index.tolist()[0]
            self.exercise = Exercise(self.exercises.loc[index,'ID'])
        if name in list(self.exercises['Exercise']):
            index = self.exercises[self.exercises['Exercise'] == name].index.tolist()[0]
            self.exercise = Exercise(self.exercises.loc[index,'ID'])

    def redo(self,note):
        delay = 0
        try: to_add = self.summary.loc[len(self.summary)-note:]
        except: print('out of range')
        for i in range(len(to_add)):
            self.exercise = Exercise(list(to_add['ID'])[i])
            weight = list(to_add['Weight'])[i]
            reps = list(to_add['Reps'])[i]
            self.add_set(weight,reps,'',delay)
            delay += 5

    def add_set(self, weight,reps,note,delay=0):
        set_dic = {i:[] for i in list(self.sets.columns)}
        load = round((self.exercise.Delta*weight+self.BW*self.exercise.kappa)*reps)
        if self.exercise.est1RL:
            intensity = round(bv_utils.epley(load/reps,reps) / self.exercise.est1RL,2)
        else: intensity = 1
        h = round(bv_utils.logistic(intensity),2)
        if self.program =='fileadd':
            set_dic['Timestamp'].append(self.startingtime+delay)
        else:
            set_dic['Timestamp'].append(datetime.datetime.now().timestamp()+delay)
        set_dic['Time'].append(self.start)
        set_dic['Number'].append(self.number)
        set_dic['Workout Name'].append(self.name)
        set_dic['Program'].append(self.program)
        set_dic['ID'].append(self.exercise.ID)
        set_dic['Exercise Name'].append(self.exercise.name)
        set_dic['Weight'].append(weight)
        set_dic['Reps'].append(reps)
        set_dic['User Weight'].append(self.BW)
        set_dic['Pred1RL'].append(round(bv_utils.epley(load/reps,reps)))
        set_dic['1RL'].append(self.exercise.est1RL)
        set_dic['Pred1RM'].append(round(bv_utils.epley(weight,reps)))
        set_dic['1RM'].append(self.exercise.est1RM)
        set_dic['Int'].append(intensity)
        set_dic['h'].append(h)
        set_dic['Load'].append(load)
        set_dic['phi'].append(load*h)
        if note: set_dic['Notes'].append(note)
        else: set_dic['Notes'].append('')
        self.sets = pd.concat((self.sets,pd.DataFrame(set_dic)),ignore_index=True)
        self.summary = pd.concat((self.summary,pd.DataFrame(set_dic)),ignore_index=True)
        self.exercise.exercise_history = self.sets[self.sets['ID'] == self.exercise.ID]
        self.exercise.est1RM = max(list(self.exercise.exercise_history['Pred1RM']))
        self.exercise.est1RL = max(list(self.exercise.exercise_history['Pred1RL']))
        self.summary.to_csv('../data/.swap.csv',index=False)

# if __name__ == '__main__':
#     bv_utils.list_exercises(sys.argv[1].upper())
