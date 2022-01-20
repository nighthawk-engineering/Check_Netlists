name = "study_netlist.py"

# -*- coding: utf-8 -*-
"""
Created on Thu Mar 14 2019

@author: mlgkschm
"""
#print('compare_netlist');exit(1)

#####################
# A note on coding style:
# 
# I like to debug as I code.
# A task is broken down into discrete functional steps that are small enough to easily test.
# Once a step is coded I will print its output, to check/test that code.
# As such, you will find lots of statements of this format:
#    #print(...); exit(1)
# Note the hash, or comment delimiter at the front.
# 
# This allows easy debugging when things go wrong. If that step has a problem I will
#  print its output and exit, which eliminates any unnecessary crap afterwards.
# 
# I also use this when reading/creating data structures. By printing the JSON
#  data structure then exiting, I can easily see what it looks like, and document it.
# 
# If you want to see what a procedure produces, simply uncomment the print();exit().
# The last printed output is the structure you're looking for.
#
# Lastly, I will also put debug print()'s within routines.
# Simply setting 'dbg' to True at the start of the routine to enable debug statements
#
#####################

#import sys
from sys import exit,argv,stderr
from getopt import getopt, GetoptError
import json
import csv
#import time
#import re
#import os
#import subprocess
#from shutil import copyfile
#from os.path import isfile,exists,basename
from sortedcontainers import SortedDict # 
from collections import deque,OrderedDict # 
from netComp import *

import pdb

#######################################################################

progname = basename(argv[0])
f_Opts = None
A_filename = None
CircuitInfo = None
Refs = None
rptFormat = None
reportPwrs = None
reportPsvs = None
numPnsList = None
pinCompare = None
refCompare = None
#
listPinCountGroups = False
printNetlist = False
useXnet = False
dumpNetlists = False
checkDbInteg = False
straightCompare = False

#####################
def showHelp():
    print('%s help:'%progname)
    print( \
'''
Available command line arguments are:
-h          -- Print this help message
-A <name>   -- Netlist A root filename
-P <name>   -- File containing JSON formatted text describing extra circuit info input to program
-O <name>   -- Use options from a file first, then command line. Command line overrides.
-d          -- Dump netlist databases (multiple files). Dump both, or use -L for only one board
-p          -- Report power nets. Both by default, or use -L <brd>
-r          -- Report shorted passives & redundant parallel connected passives. Use -L <brd>
-l          -- Print flat netlist(s). May use option -x for Xnet netlist
-n          -- Report pin count groups
-q          -- Check database integrity (validation fctn)
-m          -- Find missing pins between two refdes indicated by -M argument (validation fctn)

Arguments that select options:
-c          -- Generate reports in CSV format for other operations
-t          -- Generate reports in table format for other operations
-x          -- Use the extended net, Xnet, where applicable
-N <int>    -- Number of pin count groups to search, starting from largest
\
''')
    exit(0)

#####################
'''
Get any command line arguments
If command line arguments are being ignored (lost) in Windows
 you'll need to add "%*" to two lines in the registry that have this value:
    "C:\Python\python.exe" "%1"
 should be:
    "C:\Python\python.exe" "%1" "%*"
'''
if len(argv[1:])==1:
    args = argv[1].split()
else:
    args = argv[1:]

options = 'A:B:P:N:M:L:delmntcpqrsx'

try:
    optlist, args = getopt(args, options+'O:h')
except GetoptError as err:
    print('Error:',err,'\n', file=stderr)
    showHelp();exit(1)

Opts = OrderedDict()
for opt in optlist:
    if opt[0] == '-h':
        showHelp()
    elif opt[0] == '-O':
        with open(opt[1], 'r') as f:
            f_Opts = f.readline()
        f.close()
        f_Opts = f_Opts.split()
    else:
        Opts[opt[0]] = opt[1]

if defined(f_Opts):
    o_list = OrderedDict()
    f_Opts, args = getopt(f_Opts, options)
    for opt in f_Opts:
        o_list[opt[0]] = opt[1]
    for k,v in Opts.items():
        o_list[k] = v
    optlist = []
    for k,v in o_list.items():
        optlist.append((k,v))
#print(optlist); exit(1)

# Some options set variable used by other options. Find them first, here
for opt in optlist:
    if opt[0] == '-x':
        useXnet = True
    if opt[0] == '-c':
        rptFormat = 'CSV'
    if opt[0] == '-t':
        rptFormat = 'TXT'
    if opt[0] == '-N':
        print('Number of pin count groups to search:',opt[1])
        numPnsList = int(opt[1])

# Get values from command line arguments
for opt in optlist:
    if opt[0] == '-A':
        print('Netlist root filename:',opt[1])
        A_filename = opt[1]
    if opt[0] == '-P':
        print('Added circuit info from:',opt[1])
        CircuitInfo = opt[1]
    if opt[0] == '-l':
        print('print flat netlist')
        printNetlist = True
    if opt[0] == '-n':
        listPinCountGroups = True
    if opt[0] == '-p':
        print('Print power nets')
        reportPwrs = True
    if opt[0] == '-r':
        if rptFormat == 'CSV':
            print('"Report shorted passives & redundant, parallel passives"')
            print('"CSV format"')
        else:
            print('Report shorted passives & redundant, parallel passives')
            print('table format')
        reportPsvs = True
    if opt[0] == '-d':
        print('Dumping netlist datastructures')
        dumpNetlists = True
    if opt[0] == '-q':
        print('Checking database integrity')
        checkDbInteg = True
    if opt[0] == '-s':
        print('Straight flat netlist compare')
        straightCompare = True

#######################################################################
#######################################################################
#######################################################################
#######################################################################
'''
Read netlists here
'''
A = Netlist(filename=A_filename,filetype='Allegro')

#A.filename = A_filename

#######################################################################
## We need to add some intelligence from outside to make this easier

## Describe any nets we don't care about
# A.NoConnectList = []

## Describe nets we can ignore
# A.IgnoreList = []

###############
##

print()

###############
###############
##  SANDBOX  ##
###############
###############
##
##This is the Sandbox.  Play with methods/datas here, then delete when done
##

# How many parts are in board B?
#print('Part count',len(B.byRef));exit(1)
###############
##

#P.demoXnet('A'); exit(1)
###############
##
#print(json.dumps(A.byXnet, indent=2)); exit(1)
#print(json.dumps(B.byXnet, indent=2)); exit(1)

###############
##
#print(json.dumps(A.Xnets, indent=2)); exit(1)
#print(json.dumps(B.Xnets, indent=2)); exit(1)

###############
##
#print(A.isPassive('U4A1')); exit(1)
#print(B.isPassive('CPU1')); exit(1)

#print(A.getOtherPinNets('R6L1','1')); #exit(1)
#print(A.getOtherPinNets('R6L1','2')); exit(1)

###############
##How do we add NC pins to a part?
#
#P.reportMissingPinsByRefdes('U201','MCU1')
#A.addPins(['U201.A1','U201.U4','U201.Y1'])
#P.reportMissingPinsByRefdes('U201','MCU1')

###############
##Shaily asked for a pin_number,pin_name report on the Intel CPU:
#
# A_ref = A.byRef
# A_cpu = A_ref['U1']
# #print(json.dumps(A_cpu, indent=2))
# print('Pin Number, Pin Name,')
# for pinnum,p in A_cpu.items():
    # print('%s, %s,'%(pinnum,p['PIN_NAME']))

###############
##
#print(A.filetype)
#print(json.dumps(A.byNet, indent=2)); exit(1)

#B.byNet
#print(B.filetype)
#print(json.dumps(B.Orcad.chips, indent=2)); exit(1)
#print(json.dumps(B.Orcad.xprts, indent=2)); exit(1)
#print(json.dumps(B.Orcad.xnets, indent=2)); exit(1)

###############
##
###############
##
#print(json.dumps(A.findPowerNets(), indent=2)); exit(1)
#print('Is GND a power net? ',A.isPowerNet('GND')); exit(1)
#print('Is GND a power net? ',A.isPowerNet('GND')); exit(1)

###############
##
#exit(1)

###############
###############
###############
###############

###############
##

'''
Use this to dump all the data structures in the program.
If you want to get a list of PART_TYPEs, use this Linux command (example)
<prompt> grep PART_TYPE A_Devs_out.txt|sort|uniq > A-PART_TYPE.txt
Don't have Linux commands on your Windows machine? Install "UnxUtils" from SourceForge!
'''
if dumpNetlists:
    #print('dumping netlists')
    def dumpStruct(brd, struct, fname, rptFormat=None):
        if defined(rptFormat):
            ext = '.'+rptFormat
        else:
            ext = '.txt'
        #
        with open(fname+ext, 'w') as f:
            f.write(brd.filename+':\n')
            if defined(rptFormat) and rptFormat == 'CSV':
                for netname,pins in struct.items():
                    f.write('%s,%s\n'%(netname,','.join(pins)))
            else:
                f.write(json.dumps(struct, indent=2))
    #
    brd = 'A'
    Brd = A
    dumpStruct(Brd, Brd.byNet,    brd+'_byNet_out')
    dumpStruct(Brd, Brd.byRef,    brd+'_byRef_out')
    dumpStruct(Brd, Brd.Devs,     brd+'_Devs_out')
    dumpStruct(Brd, Brd.Refs,     brd+'_Refs_out')
    dumpStruct(Brd, Brd.Nets,     brd+'_Nets_out')
    dumpStruct(Brd, Brd.byXnet,   brd+'_byXnet_out')
    dumpStruct(Brd, Brd.flatNet,  brd+'_flatNet_out')
    dumpStruct(Brd, Brd.flatXnet, brd+'_flatXnet_out',rptFormat=rptFormat)
    dumpStruct(Brd, Brd.PowerNets,brd+'_powerNets')
    if Brd.filetype == 'OrCad':
        dumpStruct(Brd, Brd.Orcad.chips, brd+'_Orcad_chips')
        dumpStruct(Brd, Brd.Orcad.xprts, brd+'_Orcad_xprts')
        dumpStruct(Brd, Brd.Orcad.xnets, brd+'_Orcad_xnets')
        dumpStruct(Brd, Brd.Orcad.props, brd+'_Orcad_props')
    if Brd.filetype == 'Allegro':
        dumpStruct(Brd, Brd.Allegro.nets,brd+'_Allegro_nets')
        dumpStruct(Brd, Brd.Allegro.devs,brd+'_Allegro_devs')
    if Brd.filetype == 'Altium':
        dumpStruct(Brd, Brd.Altium.nets, brd+'_Altium_nets')
        dumpStruct(Brd, Brd.Altium.refs, brd+'_Altium_refs')
        dumpStruct(Brd, Brd.Altium.devs, brd+'_Altium_devs')
    #
    print('End dumping netlists')
    exit(0)

#######################################################################
if checkDbInteg:
    print('Board A: %s'%A.filename)
    A.checkDbIntegrity()
    print('\nBoard B: %s'%B.filename)
    B.checkDbIntegrity()
    exit(0)
    
###############
##
if defined(reportPwrs):
    if not defined(selectBoard) or selectBoard == 'A':
        print('%s\n%s\n'%('Board A power rails:',json.dumps(A.PowerNets, indent=2)))
    if not defined(selectBoard) or selectBoard == 'B':
        print('%s\n%s\n'%('Board B power rails:',json.dumps(B.PowerNets, indent=2)))
    exit(1)

###############
if defined(reportPsvs):
    if not defined(selectBoard) or selectBoard == 'A':
        A.reportShorted2pins(ext=rptFormat);exit(1)
    if not defined(selectBoard) or selectBoard == 'B':
        B.reportShorted2pins(ext=rptFormat);exit(1)

###############
'''
If we see a pincount discrepancy, compare pins by pincount:
'''
if defined(pinCompare):
    #print(json.dumps(list(A.byRef.keys()), indent=2)); exit(1)
    #print(json.dumps(list(B.byRef.keys()), indent=2)); exit(1)
    P.reportMissingPinsByRefdes(rRefs[0][0],Refs[0][1])
    exit(0)

###############
'''
Print a flat copy of that netlist
'''
if printNetlist:
    print('print flat copy')
    if not selectBoard in ['A','B']:
        print('ERROR: No netlist nickname "%s". Must be "A" or "B"'%selectBoard)
        exit(1)
    brd = P.getObj(selectBoard)
    brd.printNetlistByNet(useX=useXnet)
    exit(0)

###############
'''
Here's the netlist, organized by net_name->[refdes->pin, refdes->pin, ...]
'''
#print(json.dumps(A.byNet, indent=2),'\nbyNet'); exit(1)
#print(json.dumps(B.byNet, indent=2),'\nbyNet'); exit(1)

###############
'''
Here's the netlist, organized by refdes->pin->net name
'''
#print(json.dumps(A.byRef, indent=2),'\nbyRef'); exit(1)
#print(json.dumps(B.byRef, indent=2),'\nbyRef'); exit(1)

###############
'''
Here's the primitive name lookup (from RefDes) and part description data (from primitive name)
'''
#print(json.dumps(A.byNet, indent=2),'\nbyNet'); exit(1)
#print(json.dumps(B.byNet, indent=2),'\nbyNet'); exit(1)
#print(json.dumps(A.byRef, indent=2),'\nbyRef'); exit(1)
#print(json.dumps(B.byRef, indent=2),'\nbyRef'); exit(1)
#print(json.dumps(A.Refs, indent=2)); exit(1)
#print(json.dumps(B.Refs, indent=2)); exit(1)
#print(json.dumps(A.Devs, indent=2)); exit(1)
#print(json.dumps(B.Devs, indent=2)); exit(1)

#print(json.dumps(A.Refs, indent=2)); exit(1)
#print(json.dumps(A.Devs, indent=2)); exit(1)

#print(json.dumps(B.Refs, indent=2)); exit(1)
#print(json.dumps(B.Devs, indent=2)); exit(1)

###############
'''
Get the PART_NAME and VALUE properties for each REFDES
'''
#print(json.dumps(A.RefDes, indent=2),'\nRefDes'); exit(1)
#print(json.dumps(B.RefDes, indent=2)); exit(1)

###############
###############
###############

#######################################################################
#######################################################################

###############
###############
###############

###############
##
exit(0)
