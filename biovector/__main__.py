import metrics, programs, workout
import os, sys, numpy as np, pandas as pd

##### ARGS ####################################################################
#if len sys.argv
#########################################################################

# OPEN APP #########################################################################
while True:
    menu = input('[W]orkout\n[S]tats\n[I]nfo\n[U]pdate\n[Q]uit\n'+50*'*'+'\n')
    
# WORKOUT #########################################################################
    if menu == 'w':
        work = input('[C]ontinue program\n[N]ew program\n[F]ree workout\n'+50*'*'+'\n')#            
        if work in 'cnf':
            W = workout.Workout(input('Workout Name ?\n'),work)
            while W.status != 'end': W.take_input(input())
            if W.status == 'end': W.save(input('Save?\n[Yes]\n[N]o\n'+50*'*'+'\n'))
# STATS (will open GUI) #########################################################################
    if menu == 's':
        while True:
            stats = input('[B]asic\n[G]UI\n[Q]uit\n'+50*'*'+'\n')
            if stats == 'q': break
# INFO #########################################################################
    if menu == 'i':
        while True:
            print(os.system('cat ../data/sets.csv | tail -20'))
            info = input('info')
            if info == 'q': break
# UPDATE #########################################################################
    if menu == 'u':
        while True:
            update = input('Update all?\nAdd [W]eight\n[Y]es\n[Q]uit\n'+50*'*'+'\n')
            if update == 'w' : metrics.input_weight(input('weight?\n')) ; print(metrics.import_data()[2].tail())
            if update == 'y': metrics.update_all()
            if update == 'q': break
    
##### QUIT ####################################################################   
    if menu == 'q':
        break
