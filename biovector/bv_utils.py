import numpy as np, pandas as pd, math, datetime
import yaml


class Biovector:

    with open('../config.yaml') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    def __init__(self,droplist=[],selected='all'):
        if selected == 'all': selected = list(self.config['data'].keys())
        for d,p in self.config['data'].items():
            if (d not in droplist) & (d in selected):
                self.__dict__[d] = pd.read_csv(p)

    def export(self,data):
        """Export specific or all available data."""
        if data == 'all':
            for d in self.config['data']:
                if d in self.__dict__.keys():
                    self.export(d)
        if data in self.config['data'].keys():
            self.__dict__[data].to_csv(self.config['data'][data], index=False)

    def input_weight(self,string):
        """Input new weight."""
        W = {k:list(self.weight[k]) for k in self.weight.columns}
        try:
            weight = float(string)
            print('weight is ok')
            W['Date'].append(str(datetime.datetime.now())[:-7])
            W['Time'].append(datetime.datetime.now().timestamp())
            W['Weight'].append(weight)
            self.weight = pd.concat((self.weight,pd.DataFrame(W)),ignore_index=True)
            self.export('weight')
        except ValueError: print("That's no moon!!")

    def list_exercises(self,t):
        """List exercises, optionally by category."""
        print('ID, Short, Exercise')
        for i in range(len(self.exercises)):
            if t in self.exercises.loc[i,'ID']:
                print(self.exercises.loc[i,'ID'],'  ',self.exercises.loc[i,'Short'],'  ',self.exercises.loc[i,'Exercise'])


##########################################################################
#DATA MANAGMENT
########################################################################
#TO REMOVE ??
# def import_data():
#     sets = pd.read_csv('../data/sets.csv')
#     exercises = pd.read_csv('../data/exercises.csv')
#     weight = pd.read_csv('../data/measures/weight.csv')
#     workouts = pd.read_csv('../data/stats/workouts.csv')
#     return(sets,exercises,weight,workouts)

# def export_data(S=None,X=None,W=None,K=None):
#     if isinstance(S,pd.DataFrame): S.to_csv('../data/sets.csv',index=False)
#     if isinstance(X,pd.DataFrame): X.to_csv('../data/exercises.csv',index=False)
#     if isinstance(W,pd.DataFrame): W.to_csv('../data/measures/weight.csv',index=False)
#     if isinstance(K,pd.DataFrame): K.to_csv('../data/stats/workouts.csv',index=False)

#################################################################################
## CSV UPDATE
##############################################################################
class Updater(Biovector):

    def __init__(self,**kwargs):
        super().__init__(**kwargs)

    def update_all(self):
        timer_start = datetime.datetime.now().timestamp()
        print('Calculating predicted 1RM...')
        self.update_1RM()
        print('Updating bodyweight...')
        self.update_BW()
        print('Calculating workloads...')
        self.update_load()
        print('Calculating predicted 1RL...')
        self.update_1RL()
        print('Determining reference 1RM/1RL...')
        self.find_1RL_1RM()
        print('Calulating set intensities...')
        self.update_intensity()
        print('Calculating set values...')
        self.update_h()
        print('Calculating hard set workload...')
        self.update_phi()
        print('Exporting updated data...')
        self.export('all')
        print(f'Update took {datetime.datetime.now().timestamp() - timer_start} seconds.')


    def update_1RM(self,start=0,end='end'):
        """Update 1RM in sets."""
        if end == 'end': end = len(self.sets)
        weights = self.sets['Weight']
        reps = self.sets['Reps']
        self.sets['Pred1RM'] = np.around(epley(weights,reps),2)

    # Body weight
    def update_BW(self,start=0,end='end'):
        """Estimate weight based on data in weight.csv."""
        interpolation = np.interp(self.sets['Timestamp'], self.weight['Time'], self.weight['Weight'])
        self.sets['Weight'] = np.around(interpolation,2)

    # Load
    # Might change (exercise) to ID
    def update_load(self,start=0,end='end'):
        """Update loads."""
        #if end == 'end': end = len(self.sets)
        deltadic = {k:v for k,v in zip(self.exercises['ID'].values,self.exercises['Delta'].values)}
        thetadic = {k:v for k,v in zip(self.exercises['ID'].values,self.exercises['theta'].values)}
        rhodic   = {k:v for k,v in zip(self.exercises['ID'].values,self.exercises['rho'].values)}
        deltas = np.array([i if i else 0 for i in [deltadic.get(i) for i in self.sets['ID']]])
        thetas = np.array([i if i else 0 for i in [thetadic.get(i) for i in self.sets['ID']]])
        rhos   = np.array([i if i else 0 for i in [rhodic.get(i) for i in self.sets['ID']]])
        weights      = self.sets['Weight'].values
        reps         = self.sets['Reps'].values
        user_weights = self.sets['User Weight'].values
        self.sets['Load'] = (weights*deltas + user_weights*rhos*thetas) * reps
        # for i in range(len(self.exercises)):
        #     Delta = self.exercises.loc[i,'Delta']
        #     kappa = self.exercises.loc[i,'theta']*self.exercises.loc[i,'rho']
        #     for s in range(start,end):
        #         if self.sets.loc[s,'Exercise Name'] == self.exercises.loc[i,'Exercise']:
        #             self.sets.loc[s,'Load'] = (self.sets.loc[s,'Weight']*Delta + self.sets.loc[s,'User Weight']*kappa) * self.sets.loc[s,'Reps']

    def update_1RL(self,start=0,end='end'):
        """Update 1RL."""
        # if end == 'end': end = len(self.sets)
        # for i in range(start,end):
        #     self.sets.loc[i,'Pred1RL'] = epley(self.sets.loc[i,'Load']/self.sets.loc[i,'Reps'],self.sets.loc[i,'Reps'])
        loads = self.sets['Load']
        reps = self.sets['Reps']
        self.sets['Pred1RL'] = np.around(epley(loads/reps,reps),2)

    # find recent 1RL and 1RM
    def find_1RL_1RM(self,start=0,end='end'):
        """Find current 1RL 1RM."""
        if end == 'end': end = len(self.sets)
        for x in set(self.sets['Exercise Name']):
            df = self.sets[self.sets['Exercise Name'] == x]
            for i in range(start,end):
                if self.sets.loc[i,'Exercise Name'] == x:
                    self.sets.loc[i,'1RL'] = np.array(df.loc[:i,'Pred1RL']).max()
                    self.sets.loc[i,'1RM'] = np.array(df.loc[:i,'Pred1RM']).max()

    def update_intensity(self,start=0,end='end'):
        """Update intensity."""
        if end == 'end': end = len(self.sets)
        for i in range(start,end):
            self.sets.loc[i,'Int'] = self.sets.loc[i,'Pred1RL']/self.sets.loc[i,'1RL']

    def update_h(self,start=0,end='end'):
        """Update set hardness."""
        if end == 'end': end = len(self.sets)
        for i in range(start,end):
            self.sets.loc[i,'h'] = logistic(self.sets.loc[i,'Int'])

    def update_phi(self,start=0,end='end'):
        """Update volume of hard sets."""
        if end == 'end': end = len(self.sets)
        for i in range(start,end):
            self.sets.loc[i,'phi'] = self.sets.loc[i,'Load'] * self.sets.loc[i,'h']


###############################################

##########################################################
def logistic(x):
    return 1.05/(1+math.e**(-40*(x-0.75)))

def epley(weight,reps):
    return weight*(1+ reps/30)


def translate(strg):
    """Return (exercise,weight,reps,note,status) inferred from user input."""
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


# if __name__ == '__main__':
#     update_all()
    #S,*trash = import_data()
    #print('Weird K rebuild') #to remove
    #update_K(S,st1=0,st2=0) #to remove
