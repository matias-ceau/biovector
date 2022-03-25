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
