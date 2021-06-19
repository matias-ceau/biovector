import os, sys, numpy as np, pandas as pd, datetime
import metrics, programs

def list_exercises(t):
        data = metrics.import_data()[1]
        print('ID, Short, Exercise')
        for i in range(len(data)):
            if t in data.loc[i,'ID']:
                print(data.loc[i,'ID'],'  ',data.loc[i,'Short'],'  ',data.loc[i,'Exercise'])

#######################################################################################

class Exercise:
    def __init__(self,ID):
        self.ID = ID
        self.all_S = metrics.import_data()[0]
        self.all_X = metrics.import_data()[1]
        self.cur_S = self.all_S[self.all_S['ID'] == ID] #set history
        self.cur_X = self.all_X[self.all_X['ID'] == ID] #exercise data
        self.name = list(self.cur_X['Exercise'])[0]
        self.Delta = list(self.cur_X['Delta'])[0]
        self.kappa = list(self.cur_X['kappa'])[0]
        self.Short = list(self.cur_X['Short'])[0]
        self.est1RM = max(list(self.cur_S['Pred1RM'])+[0])
        self.est1RL = max(list(self.cur_S['Pred1RL'])+[0])

#######################################################################################

class Workout:
    def __init__(self,name,program=None,t=0):
        self.name = name
        if program in 'c': self.program = programs.default
        if program == 'w': self.program = 'workout'
        if program == 'f': self.program = 'free'
        if program == 'n':
            for i in range(len(programs.choice)): print(i+1,':',programs.choice[i])
            self.program = programs.choice[int(input('Type number!'))]
        if self.program == 'fileadd':
            self.startingtime == t
        else:
            self.startingtime = datetime.datetime.now()
        self.start = self.startingtime.strftime("%Y-%m-%d %H:%M:%S")
        self.all_S = metrics.import_data()[0]
        self.all_X = metrics.import_data()[1]
        self.all_W = metrics.import_data()[2]
        self.all_K = metrics.import_data()[3]
        self.summary = pd.DataFrame({i:[] for i in list(self.all_S.columns)})
        self.BW = self.all_W.loc[len(self.all_W)-1,'Weight']
        if self.program == 'free': 
            self.number = 0
        else:
            self.number = int(max(list(self.all_S.loc[:,'Number'])) + 1)
        self.exercise = None
        self.weight = None
        self.status = 'active' 
        self.template = None
        for i in [t+n for t in [str(i) for i in range(1,7)] for n in 'ABC']:
            if i in self.name:
                self.week,self.L = i
                self.template = programs.Monolith(self.week,self.L)
    
    def take_input(self, user_input):
        exercise, weight, reps, note, status = self.translate(user_input)
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
            list_exercises(note)
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

    def program_print(self,week,L):
        print(programs.Monolith(week,L))
    
    def save(self,strg):
        if strg != 'n': 
            metrics.export_data(S=self.all_S)
        if self.number != 0:
            self.all_K = self.all_K.append(pd.DataFrame({'Number':[self.number],
                                                         'Timestamp':[self.startingtime.timestamp()],
                                                         'Date':[self.startingtime],
                                                         'Hardsets':[sum(list(self.summary.loc[:,'h']))],
                                                         'Load':[sum(list(self.summary.loc[:,'Load']))],
                                                         'Hardload':[sum(list(self.summary.loc[:,'phi']))]}),ignore_index=True)
            metrics.export_data(K=self.all_K)
    
    def translate(self, strg):
        '''returns (exercise,weight,reps,note,status)'''
#        # /
#        if '/' in strg:
#            try: return(None,None,None,None,'note')
#            except: note = None
        # @
        if '@' in strg:
            try: return (None,None,None,strg.split('@')[-1],'template')
            except: return (None,None,None,None,'template')
        # $
        if '$' in strg: return (None,None,None,None,'todo')
        # redo
        if '!' in strg:
            try: note = int(strg.split('!')[0])
            except: note = 1
            return (None,None,None,note,'redo')
        # delete
        if 'delete' in strg:
            try: note = strg.split('delete')[1]
            except: note = 1
            return (None,None,None,note,'delete')
        # help
        if 'help' in strg:
            try: note = strg.split('help')[1]
            except: note = None
            return (None,None,None,note,'help')
        # quit
        if 'quit' in strg: return (None,None,None,None,'end') # help
        # set
        s = strg.split(' ')
        if len(s) == 3:
            try: return (s[0],float(s[1]),int(s[2]),None,'active')
            except: pass
        if len(s) == 2:
            try: return (None,float(s[0]),int(s[1]),None,'active')
            except: pass
            try: return (s[0],None,int(s[1]),None,'active')
            except: pass
        if len(s) == 1:
            if s[0].isdigit(): return (None,None,int(s[0]),None,'active')
            else: return (s[0],None,None,None,'active')
        return(None,None,None,None,None)

    def delete_set(self,n=1):
        try: n = int(n)
        except: n = 1
        if len(self.summary) < n:
            print("You're trying to delete previous sets!\n")
        else:
            self.all_S = self.all_S.iloc[:-n,:]
            self.summary = self.summary.iloc[:-n,:]
            self.exercise = Exercise(self.exercise.ID)
    
    def print_summary(self):
        duration = str(datetime.datetime.now() - self.startingtime)[:-7]
        Phi = int(sum(list(self.summary['phi'])))
        H = round(sum(list(self.summary['h'])),1)
        print('*'*70,'\n')
        print("{:^20}\n{:^20}\n{:^20}\n{:^20}\n{:^20}\n{:^20}\n{:^20}".format(self.name, self.number,self.program, self.start, duration, str(Phi)+' kg-m', str(H)+' hard sets'))
        print('{:^20}{:<7}{:<3} {:<4} {:<4}  {:<4} {:<5} {:<2}'.format('', 'W', 'R', '1RM', 'Best', '1RL', 'I', 'h'))
        for i in range(len(self.summary)): 
            exo, reps, weight, rm, predrm, predrl, its, h = self.summary.loc[i,'Exercise Name'], self.summary.loc[i,'Reps'], self.summary.loc[i,'Weight'], self.summary.loc[i,'1RM'], self.summary.loc[i,'Pred1RM'], self.summary.loc[i,'Pred1RL'], self.summary.loc[i,'Int'], self.summary.loc[i,'h'] 
            print("{:^20}{:<7}{:<3} {:<4} {:<4}  {:<4} {:<4.0%} {:<2}".format(exo,weight, int(reps), round(predrm), round(rm), round(predrl), its, round(h,1)))
        print('*'*70)
            
    def choose_exercise(self,name):
        if name in list(self.all_X['ID']):
            self.exercise = Exercise(name)
        if name in list(self.all_X['Short']):
            index = self.all_X[self.all_X['Short'] == name].index.tolist()[0]
            self.exercise = Exercise(self.all_X.loc[index,'ID'])
        if name in list(self.all_X['Exercise']):
            index = self.all_X[self.all_X['Exercise'] == name].index.tolist()[0]
            self.exercise = Exercise(self.all_X.loc[index,'ID'])
    
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
        set_dic = {i:[] for i in list(self.all_S.columns)}
        load = (self.exercise.Delta*weight+self.BW*self.exercise.kappa)*reps
        if self.exercise.est1RL:
            intensity = metrics.epley(load/reps,reps) / self.exercise.est1RL
        else: intensity = 1
        h = metrics.logistic(intensity)
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
        set_dic['Pred1RL'].append(metrics.epley(load/reps,reps))
        set_dic['1RL'].append(self.exercise.est1RL)
        set_dic['Pred1RM'].append(metrics.epley(weight,reps))
        set_dic['1RM'].append(self.exercise.est1RM)
        set_dic['Int'].append(intensity)
        set_dic['h'].append(h)
        set_dic['Load'].append(load)
        set_dic['phi'].append(load*h)
        if note: set_dic['Notes'].append(note)
        else: set_dic['Notes'].append('')
        self.all_S = self.all_S.append(pd.DataFrame(set_dic),ignore_index=True)
        self.summary = self.summary.append(pd.DataFrame(set_dic),ignore_index=True) 
        self.exercise.cur_S = self.all_S[self.all_S['ID'] == self.exercise.ID]
        self.exercise.est1RM = max(list(self.exercise.cur_S['Pred1RM']))
        self.exercise.est1RL = max(list(self.exercise.cur_S['Pred1RL']))
        self.summary.to_csv('../data/.swap.csv',index=False)
        
if __name__ == '__main__':
    list_exercises('C')
