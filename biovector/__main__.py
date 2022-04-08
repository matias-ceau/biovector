import argparse


parser = argparse.ArgumentParser(prog=('biovector'),
                                 description='biovector',
                                 epilog='this is the epilog')
parser.add_argument('cmd',choices = [1,2],nargs='?',default='ls')
parser.add_argument('-i', '--ID',nargs='+', type=int)
parser.add_argument('-C','--category')
parser.add_argument('-N','--name',nargs='+')
parser.add_argument('-I','--instrument',nargs='+')
parser.add_argument('-t','--tags',nargs='+')
parser.add_argument('-d','--description',nargs='*') #nargs???
parser.add_argument('-l','--links',nargs='+')
parser.add_argument('-f','--file')
parser.add_argument('-p','--priority')
parser.add_argument('--verbose', '-v', action='count', default=0)
parser.add_argument('-s','--status', type=int)
parser.add_argument('-g', '--goal',type=int)
parser.add_argument('-u','--urg')
parser.add_argument('--created')
parser.add_argument('--log')
parser.add_argument('--count',type=int)

a = parser.parse_args()

#cmd as a list
if cmd[1] ==: 'set' #add, ls, mod                        ##: -0
if cmd[1] ==: 'workout' #new, ls, update (tm changed)    ##: -n
if cmd[1] ==: 'measures' #add, ls,                       ##: -bw -bf
if cmd[1] ==: 'program' #show #create instnace 1rm weekly yearly etc
if cmd[1] ==: 'interactive'
if cmd[1] ==: 'config' #TM, current program
if cmd[1] ==: 'interactive'
if cmd[1] ==: 'update' #update all, update specific

#FILES
# main data : exercises,sets
# measures : bodyweight + the rest
# program instances

# SCRIPTS
# __main__, workout, interactive, stats, bv_utils, programs
