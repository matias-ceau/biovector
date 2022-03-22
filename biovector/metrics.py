import numpy as np, pandas as pd, math, datetime


########################################################################
def import_data():
    sets = pd.read_csv('../data/sets.csv')
    exercises = pd.read_csv('../data/exercises.csv')
    weight = pd.read_csv('../data/weight.csv')
    workouts = pd.read_csv('../data/workouts.csv')
    return(sets,exercises,weight,workouts)

def export_data(S=None,X=None,W=None,K=None):
    if isinstance(S,pd.DataFrame): S.to_csv('../data/sets.csv',index=False)
    if isinstance(X,pd.DataFrame): X.to_csv('../data/exercises.csv',index=False)
    if isinstance(W,pd.DataFrame): W.to_csv('../data/weight.csv',index=False)
    if isinstance(K,pd.DataFrame): K.to_csv('../data/workouts.csv',index=False)

# 1RM
def update_1RM(S,start=0,end='end'):
    '''Updates 1RM in sets'''
    if end == 'end': end = len(S)
    for i in range(start,end):
        S.loc[i,'Pred1RM'] = epley(S.loc[i,'Weight'],S.loc[i,'Reps'])

# Update kappa
def update_kappa(X):
    '''Updates kappa in exercises.csv'''
    for i in range(len(X)):
        X.loc[i,'kappa'] = X.loc[i,'rho'] * X.loc[i,'theta']

# Body weight
def update_BW(W,S,start=0,end='end'):
    '''Estimates weight based on data in weight.csv'''
    if end == 'end': end = len(S)
    for i in range(start,end):
        if S.loc[i,'Timestamp'] <= W.loc[0,'Time'] : S.loc[i,'User Weight'] = W.loc[0,'Weight']
        if S.loc[i,'Timestamp'] >= W.loc[len(W)-1,'Time'] : S.loc[i,'User Weight'] = W.loc[len(W)-1,'Weight']
        else:
            for t in range(len(W)-1): #really -1
                if W.loc[t,'Time'] < S.loc[i,'Timestamp'] < W.loc[t+1,'Time']:
                    ratio = (W.loc[t+1,'Time'] - S.loc[i,'Timestamp'])/(W.loc[t+1,'Time'] -  W.loc[t,'Time'])
                    weight_delta = (W.loc[t+1,'Weight'] -  W.loc[t,'Weight']) * ratio
                    S.loc[i,'User Weight'] = W.loc[t,'Weight'] + weight_delta
        
# Load
# Might change (exercise) to ID
def update_load(X,S,start=0,end='end'):
    '''Updates loads'''
    if end == 'end': end = len(S)
    for i in range(len(X)):
        Delta = X.loc[i,'Delta']
        kappa = X.loc[i,'kappa']
        for s in range(start,end):
            if S.loc[s,'Exercise Name'] == X.loc[i,'Exercise']:
                S.loc[s,'Load'] = (S.loc[s,'Weight']*Delta + S.loc[s,'User Weight']*kappa) * S.loc[s,'Reps']

def update_1RL(S,start=0,end='end'):
    '''Updates 1RL'''
    if end == 'end': end = len(S)
    for i in range(start,end):
        S.loc[i,'Pred1RL'] = epley(S.loc[i,'Load']/S.loc[i,'Reps'],S.loc[i,'Reps'])

    
# find recent 1RL and 1RM
def find_1RL_1RM(S,start=0,end='end'):
    '''Finds current 1RL 1RM'''
    if end == 'end': end = len(S)
    for x in set(S['Exercise Name']):
        df = S[S['Exercise Name'] == x]
        for i in range(start,end):
            if S.loc[i,'Exercise Name'] == x:
                S.loc[i,'1RL'] = np.array(df.loc[:i,'Pred1RL']).max()
                S.loc[i,'1RM'] = np.array(df.loc[:i,'Pred1RM']).max()
                
def update_intensity(S,start=0,end='end'):
    if end == 'end': end = len(S)
    for i in range(start,end):
        S.loc[i,'Int'] = S.loc[i,'Pred1RL']/S.loc[i,'1RL']
        
def update_h(S,start=0,end='end'):
    if end == 'end': end = len(S)
    for i in range(start,end):
        S.loc[i,'h'] = logistic(S.loc[i,'Int'])
        
def update_phi(S,start=0,end='end'):
    if end == 'end': end = len(S)
    for i in range(start,end):
        S.loc[i,'phi'] = S.loc[i,'Load'] * S.loc[i,'h']

def logistic(x):
    return 1.05/(1+math.e**(-40*(x-0.75)))

def epley(weight,reps):
    return weight*(1+ reps/30)

def update_K(S,st1=0,st2=0):
    '''Not in use in main at the moment'''
    nb = list(set(S['Number'])) ; nb.sort() ; emp = len(nb)*[0]
    K = pd.DataFrame({'Number':nb,'Timestamp':emp,'Date':emp,'Hardsets':emp,'Load':emp,'Hardload':emp,'Notes':emp})
    for i in range(st1,len(S)):
        for j in range(st2,len(K)):
            if S.loc[i,'Number'] == K.loc[j,'Number']:
                K.loc[j,'Timestamp'] = S.loc[i,'Timestamp']
                K.loc[j,'Date'] = S.loc[i,'Time']
                K.loc[j,'Hardsets'] += S.loc[i,'h']
                K.loc[j,'Load'] += S.loc[i,'Load']
                K.loc[j,'Hardload'] += S.loc[i,'phi']
    export_data(K=K)
###################################################################""
def update_all():
    S,X,W,K = import_data()
    timer_start = datetime.datetime.now().timestamp()
    print('Calculating predicted 1RM...')
    update_1RM(S)
    print('Updating kappa coefficient...')
    update_kappa(X)
    print('Updating bodyweight...')
    update_BW(W,S)
    print('Calculating workloads...')
    update_load(X,S)
    print('Calculating predicted 1RL...')
    update_1RL(S)
    print('Determining reference 1RM/1RL...')
    find_1RL_1RM(S)
    print('Calulating set intensities...')
    update_intensity(S)
    print('Calculating set values...')
    update_h(S)
    print('Calculating hard set workload...')
    update_phi(S)
    print('Exporting updated data...')
    export_data(S,X,W,K)
    print(f'Update took {datetime.datetime.now().timestamp() - timer_start} seconds.')


#############" WEIGHT
def input_weight(string):
    D = import_data()[2]
    W = {k:list(D[k]) for k in D.columns}
    try: 
        weight = float(string)
        print('weight is ok')
        W['Date'].append(str(datetime.datetime.now())[:-7])
        W['Time'].append(datetime.datetime.now().timestamp())
        W['Weight'].append(weight)
        N = pd.DataFrame(W)
        N.to_csv('../data/weight.csv',index=False)
    except ValueError: print("That's no moon!!")

if __name__ == '__main__':
    update_all()
    #S,*trash = import_data()
    #print('Weird K rebuild') #to remove
    #update_K(S,st1=0,st2=0) #to remove
