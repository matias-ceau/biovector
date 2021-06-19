import pandas as pd, numpy as np
import metrics

def sel_1RM_finder(d,start=0,end='end',e=1):
    global sets
    if end=='end':end=len(sets)
    k = (datetime.datetime.now()-datetime.timedelta(days = d)).timestamp()
    while end-start>e:
        m = round((start+end)/2)
        if np.array(sets['Timestamp'])[m] >k: end = m
        else: start = m
    selsets = sets.loc[m:,:]
    dic = {k:0 for k in ['S00','H00.0','P10.0','P01.00']}
    for x in dic.keys():
        ex_list = list(selsets[selsets['ID'] == x]['Pred1RM'])
        if ex_list: dic[x] = round(max(ex_list))
    return dic
