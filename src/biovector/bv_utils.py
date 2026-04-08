import numpy as np
import pandas as pd
import math
import datetime
import yaml
import os
import shutil
from pathlib import Path


class Biovector:

    PACKAGE_DIR = Path(__file__).resolve().parent
    CONFIG = PACKAGE_DIR / "config.yaml"
    SEED_DATA_DIR = PACKAGE_DIR / "data"
    DATA_DIR_ENV_VAR = "BIOVECTOR_DATA_DIR"
    DEFAULT_DATA_DIR = Path.home() / ".local" / "share" / "biovector"
    with open(CONFIG) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    def __init__(self,droplist=[],selected='all'):
        self.data_dir = self.resolve_data_dir()
        self._bootstrap_runtime_data()
        if selected == 'all': selected = list(self.config['paths'].keys())
        for d,p in self.config['paths'].items():
            if (d not in droplist) & (d in selected):
                self.__dict__[d] = pd.read_csv(self.dataset_path(d))

    @classmethod
    def resolve_data_dir(cls):
        configured = os.getenv(cls.DATA_DIR_ENV_VAR)
        if configured:
            path = Path(configured).expanduser()
        elif cls.SEED_DATA_DIR.exists() and (cls.SEED_DATA_DIR / "sets.csv").exists():
            # Use repo data if available (editable install)
            path = cls.SEED_DATA_DIR
        else:
            path = cls.DEFAULT_DATA_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def dataset_path(cls, dataset_name):
        if dataset_name not in cls.config["paths"]:
            raise KeyError(f"Unknown dataset: {dataset_name}")
        return cls.resolve_data_dir() / cls.config["paths"][dataset_name]

    @classmethod
    def swap_path(cls):
        return cls.resolve_data_dir() / ".swap.csv"

    def _bootstrap_runtime_data(self):
        for dataset_name in self.config["paths"]:
            runtime_path = self.dataset_path(dataset_name)
            if runtime_path.exists():
                continue

            seed_path = self.SEED_DATA_DIR / self.config["paths"][dataset_name]
            if seed_path.exists():
                runtime_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(seed_path, runtime_path)
                continue

            runtime_path.parent.mkdir(parents=True, exist_ok=True)
            if dataset_name == "weight":
                now = datetime.datetime.now()
                pd.DataFrame([{
                    "Date": str(now)[:-7],
                    "Time": now.timestamp(),
                    "Weight": 0.0,
                }]).to_csv(runtime_path, index=False)
            elif dataset_name == "workouts":
                pd.DataFrame(columns=[
                    "Number",
                    "Timestamp",
                    "Date",
                    "Hardsets",
                    "Load",
                    "Hardload",
                    "Notes",
                ]).to_csv(runtime_path, index=False)
            elif dataset_name == "cardio":
                pd.DataFrame(columns=[
                    "Timestamp",
                    "Date",
                    "Workout Name",
                    "Type",
                    "DurationSec",
                    "DistanceKm",
                    "AvgHeartRate",
                    "Calories",
                    "Notes",
                ]).to_csv(runtime_path, index=False)
            elif dataset_name == "kettlebell":
                pd.DataFrame(columns=[
                    "Timestamp",
                    "Date",
                    "Workout Name",
                    "Exercise",
                    "WeightKg",
                    "Reps",
                    "Sets",
                    "Style",
                    "DurationSec",
                    "Notes",
                ]).to_csv(runtime_path, index=False)
            elif dataset_name == "imports":
                pd.DataFrame(columns=[
                    "Timestamp",
                    "Source",
                    "FilePath",
                    "ImportedRows",
                    "Status",
                    "Notes",
                ]).to_csv(runtime_path, index=False)
            elif dataset_name == "ocr_notes":
                pd.DataFrame(columns=[
                    "Timestamp",
                    "SourceImage",
                    "RawText",
                    "ParsedType",
                    "Confidence",
                    "Status",
                    "Notes",
                ]).to_csv(runtime_path, index=False)
            else:
                raise FileNotFoundError(
                    f"Missing seed data for required dataset '{dataset_name}' at {seed_path}"
                )

    def append_record(self, dataset_name, record):
        if dataset_name not in self.config["paths"]:
            raise KeyError(f"Unknown dataset: {dataset_name}")
        frame = pd.read_csv(self.dataset_path(dataset_name))
        frame = pd.concat((frame, pd.DataFrame([record])), ignore_index=True)
        frame.to_csv(self.dataset_path(dataset_name), index=False)
        if hasattr(self, dataset_name):
            self.__dict__[dataset_name] = frame

    def import_records_from_csv(self, source, source_path, target_dataset, mapping=None):
        if target_dataset not in self.config["paths"]:
            raise KeyError(f"Unknown target dataset: {target_dataset}")
        incoming = pd.read_csv(source_path)
        if mapping:
            incoming = incoming.rename(columns=mapping)
        target_path = self.dataset_path(target_dataset)
        existing = pd.read_csv(target_path)
        missing = [c for c in existing.columns if c not in incoming.columns]
        for column in missing:
            incoming[column] = np.nan
        incoming = incoming[existing.columns]
        merged = pd.concat((existing, incoming), ignore_index=True)
        merged.to_csv(target_path, index=False)
        if hasattr(self, target_dataset):
            self.__dict__[target_dataset] = merged

        self.append_record("imports", {
            "Timestamp": datetime.datetime.now().timestamp(),
            "Source": source,
            "FilePath": source_path,
            "ImportedRows": len(incoming),
            "Status": "ok",
            "Notes": "",
        })
        return len(incoming)

    def add_ocr_note(self, source_image, raw_text, parsed_type="unknown", confidence=0.0, status="pending", notes=""):
        self.append_record("ocr_notes", {
            "Timestamp": datetime.datetime.now().timestamp(),
            "SourceImage": source_image,
            "RawText": raw_text,
            "ParsedType": parsed_type,
            "Confidence": confidence,
            "Status": status,
            "Notes": notes,
        })

    @staticmethod
    def parse_ocr_text(raw_text):
        lower = raw_text.lower()
        if "kb" in lower or "kettlebell" in lower:
            return "kettlebell", 0.7
        if "km" in lower or "run" in lower or "cardio" in lower:
            return "cardio", 0.7
        return "unknown", 0.3

    def export(self,data):
        """Export specific or all available data."""
        if data == 'all':
            for d in self.config['paths']:
                if d in self.__dict__.keys():
                    self.export(d)
        if data in self.config['paths'].keys():
            self.__dict__[data].to_csv(self.dataset_path(data), index=False)

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


    def update_1RM(self):
        """Update 1RM in sets."""
        self.sets['Pred1RM'] = np.around(epley(self.sets['Weight'], self.sets['Reps']))

    # Body weight
    def update_BW(self):
        """Estimate weight based on data in weight.csv."""
        interpolation = np.interp(self.sets['Timestamp'], self.weight['Time'], self.weight['Weight'])
        self.sets['User Weight'] = np.around(interpolation,1)

    # Load
    # Might change (exercise) to ID
    def update_load(self):
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
        self.sets['Load'] = np.around((weights*deltas + user_weights*rhos*thetas) * reps)
        # for i in range(len(self.exercises)):
        #     Delta = self.exercises.loc[i,'Delta']
        #     kappa = self.exercises.loc[i,'theta']*self.exercises.loc[i,'rho']
        #     for s in range(start,end):
        #         if self.sets.loc[s,'Exercise Name'] == self.exercises.loc[i,'Exercise']:
        #             self.sets.loc[s,'Load'] = (self.sets.loc[s,'Weight']*Delta + self.sets.loc[s,'User Weight']*kappa) * self.sets.loc[s,'Reps']

    def update_1RL(self):
        """Update 1RL."""
        # if end == 'end': end = len(self.sets)
        # for i in range(start,end):
        #     self.sets.loc[i,'Pred1RL'] = epley(self.sets.loc[i,'Load']/self.sets.loc[i,'Reps'],self.sets.loc[i,'Reps'])
        self.sets['Pred1RL'] = np.around(epley(self.sets['Load']/self.sets['Reps'],self.sets['Reps']))

    # find recent 1RL and 1RM #here
    def find_1RL_1RM(self):
        """Find current 1RL 1RM."""
        # if end == 'end': end = len(self.sets)
        # for x in set(self.sets['Exercise Name']):
        #     df = self.sets[self.sets['Exercise Name'] == x]
        #     for i in range(start,end):
        #         if self.sets.loc[i,'Exercise Name'] == x:
        #             self.sets.loc[i,'1RL'] = np.array(df.loc[:i,'Pred1RL']).max()
        #             self.sets.loc[i,'1RM'] = np.array(df.loc[:i,'Pred1RM']).max()
        all_exercises = set(self.sets['Exercise Name'])
        for write,read in [('1RL','Pred1RL'),('1RM','Pred1RM')]:
            dic = {x : pd.Series(self.sets[self.sets['Exercise Name']==x][read].values,index=self.sets[self.sets['Exercise Name']==x].index) for x in all_exercises}
            for x,d in dic.items():
                dic[x] = pd.Series([d.values[0]] +[max(d.values[:i]) for i in range(1,len(d))],index=d.index)
            a = pd.concat([v for k,v in dic.items()]).sort_index()
            self.sets.loc[a.index, write] = np.around(a.values)

    def update_intensity(self):
        """Update intensity."""
        self.sets.loc[:,'Int'] = np.around(self.sets.loc[:,'Pred1RL']/self.sets.loc[:,'1RL'],2)

    def update_h(self):
        """Update set hardness."""
        self.sets.loc[:,'h'] = np.around(logistic(self.sets.loc[:,'Int']),2)

    def update_phi(self):
        """Update volume of hard sets."""
        self.sets.loc[:,'phi'] = np.around(self.sets.loc[:,'Load'] * self.sets.loc[:,'h'])


###############################################

##########################################################
def logistic(x):
    """Return hard set index when inputed proportion."""
    return 1.05/(1+math.e**(-40*(x-0.75)))

def epley(weight,reps):
    """Estimate 1RM."""
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
