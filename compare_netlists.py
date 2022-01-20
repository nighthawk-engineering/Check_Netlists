name = "compare_netlists.py"

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
B_filename = None
CircuitInfo = None
Refs = None
rptFormat = None
reportPwrs = None
reportPsvs = None
numPnsList = None
pinCompare = None
refCompare = None
selectBoard = None
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
-B <name>   -- Netlist B root filename
-P <name>   -- File containing JSON formatted text describing extra circuit info input to program
-O <name>   -- Use options from a file first, then command line. Command line overrides.
-d          -- Dump netlist databases (multiple files). Dump both, or use -L for only one board
-p          -- Report power nets. Both by default, or use -L <brd>
-r          -- Report shorted passives & redundant parallel connected passives. Use -L <brd>
-l          -- Print flat netlist(s). May use option -x for Xnet netlist
-s          -- Straight-up flat netlist compare of A & B (Xnet not available)
-e          -- Compare nets on two refdes using -M argument
-n          -- Report pin count groups
-q          -- Check database integrity (validation fctn)
-m          -- Find missing pins between two refdes indicated by -M argument (validation fctn)

Arguments that select options:
-c          -- Generate reports in CSV format for other operations
-t          -- Generate reports in table format for other operations
-x          -- Use the extended net, Xnet, where applicable
-L <brd>    -- Select board 'A' or 'B' for other operations
-M <Refs>   -- Specify two refdes for -m and -e. Refs looks like "A.U201,B.MCU1"
-N <int>    -- Number of pin count groups to search, starting from largest
\
''')
    exit(0)

#####################
'''
Get any command line arguments
If command line arguments are being ignored in Windows
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
    if opt[0] == '-L':
        selectBoard = opt[1]
        if not selectBoard in ['A','B']:
            print('Error: option -L: must select board A or B',file=stderr);exit(1)
        print('Board %s selected'%selectBoard)
    if opt[0] == '-M':
        Refs = opt[1].split(',')
        print('Two refdes referenced: %s and %s'%(Refs[0],Refs[1]))
        Refs = [Refs[0].split('.'), Refs[1].split('.')]; 
    if opt[0] == '-N':
        print('Number of pin count groups to search:',opt[1])
        numPnsList = int(opt[1])

# Get values from command line arguments
for opt in optlist:
    if opt[0] == '-A':
        print('Netlist A root filename:',opt[1])
        A_filename = opt[1]
    if opt[0] == '-B':
        print('Netlist B root filename:',opt[1])
        B_filename = opt[1]
    if opt[0] == '-P':
        print('Added circuit info from:',opt[1])
        CircuitInfo = opt[1]
    if opt[0] == '-e':
        if not defined(Refs):
            print('Error: Must specify two refdes for -e operation',file=stderr);exit(1)
        refCompare = True
    if opt[0] == '-l':
        print('print flat netlist')
        printNetlist = True
    if opt[0] == '-m':
        if not defined(Refs):
            print('Error: Must specify two refdes for -m operation',file=stderr);exit(1)
        pinCompare = True
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

if not defined(A_filename) or not defined(B_filename):
    print('ERROR: Must have filenames for both boards A and B\n')
    showHelp()

#######################################################################
#######################################################################
#######################################################################
#######################################################################
'''
Read netlists here
'''
A = Netlist(filename=A_filename)
B = Netlist(filename=B_filename)

#A.filename = A_filename
#++9*-+9+++++++-9+9+++-**********++++++++++++++++B.filename = B_filename

P = twoLists(A,B)

#props = readOrcadPropExport(B.filename)
#props = readOrcadEmptyProp(B.filename)
#print(json.dumps(props, indent=2)); exit(1)
# for ref,pinsDct in props['PINS'].items():
    # for pin,propDct in pinsDct.items():
        # if propDct['Insert'] == "NI":
            # print('%s: %s'%(ref,propDct['Insert']))
    # print()
#exit(1)
#######################################################################
## We need to add some intelligence from outside to make this easier

## Import external knowledge about the design
if defined(CircuitInfo):
    NewCktInfo = json.loads(readFile(CircuitInfo))
    #print(json.dumps(NewCktInfo, indent=2)); exit(1)
    #
    A.Actives = NewCktInfo['A_PART_TYPE2']  # Board A active components
    B.Actives = NewCktInfo['B_PART_TYPE2']  # Board B active components
    A.NoConnectList = NewCktInfo['A_NO_CONNECT_LIST']  # Board A no connect list
    B.NoConnectList = NewCktInfo['B_NO_CONNECT_LIST']  # Board B no connect list
    A.IgnoreList = NewCktInfo['A_IGNORE_LIST']  # Board A netname ignore list
    B.IgnoreList = NewCktInfo['B_IGNORE_LIST']  # Board B netname ignore list
    A.ConnectorList = NewCktInfo['A_CONNECTOR_LIST']  # Board A netname Connector list
    B.ConnectorList = NewCktInfo['B_CONNECTOR_LIST']  # Board B netname Connector list
    A.PwrGndAdded = NewCktInfo['A_PWRGND_LIST']  # Board A netname PowerGround list
    B.PwrGndAdded = NewCktInfo['B_PWRGND_LIST']  # Board B netname PowerGround list
    #
    P.refdesPairs = NewCktInfo['REFDES_PAIRS']  # for matching to Intel ref, if that ever happens

## Describe equivalent parts between the boards, by reference
# RefdesPairs = SortedDict({  
    # 'CPU': {'A':'U5E1', 'B':'CPU1'},  
    # 'PCH': {'A':'U7B1', 'B':'PCH1'},  
    # 'SNI': {'A':'U7H1', 'B':'SNI1'}   
# })
#P.refdesPairs = RefdesPairs  # for matching to Intel ref, if that ever happens

## Describe any nets we don't care about
# A.NoConnectList = []
# B.NoConnectList = ['NC']  # list of nets of no consequence which muck things up

## Describe nets we can ignore
# A.IgnoreList = []
# B.IgnoreList = []

#######################################################################
## How many from the pin count list shall we examine?
P.numPnsList = numPnsList  # from command line

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

if straightCompare:
    P.straightNetlistCompare()
    exit(1)
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
    def dumpStruct(brd, struct, fname):
        with open(fname, 'w') as f:
            f.write(brd.filename+':\n')
            f.write(json.dumps(struct, indent=2))
    #
    for brd in ['A','B']:
        if not defined(selectBoard) or selectBoard == brd:
            Brd = P.Netlist[brd]
            dumpStruct(Brd, Brd.byNet,    brd+'_byNet_out.txt')
            dumpStruct(Brd, Brd.byRef,    brd+'_byRef_out.txt')
            dumpStruct(Brd, Brd.Devs,     brd+'_Devs_out.txt')
            dumpStruct(Brd, Brd.Refs,     brd+'_Refs_out.txt')
            dumpStruct(Brd, Brd.Nets,     brd+'_Nets_out.txt')
            dumpStruct(Brd, Brd.byXnet,   brd+'_byXnet_out.txt')
            dumpStruct(Brd, Brd.flatNet,  brd+'_flatNet_out.txt')
            dumpStruct(Brd, Brd.flatXnet, brd+'_flatXnet_out.txt')
            dumpStruct(Brd, Brd.PowerNets,brd+'_powerNets.txt')
            if Brd.filetype == 'OrCad':
                dumpStruct(Brd, Brd.Orcad.chips, brd+'_Orcad_chips.txt')
                dumpStruct(Brd, Brd.Orcad.xprts, brd+'_Orcad_xprts.txt')
                dumpStruct(Brd, Brd.Orcad.xnets, brd+'_Orcad_xnets.txt')
                dumpStruct(Brd, Brd.Orcad.props, brd+'_Orcad_props.txt')
            if Brd.filetype == 'Allegro':
                dumpStruct(Brd, Brd.Allegro.nets,brd+'_Allegro_nets.txt')
                dumpStruct(Brd, Brd.Allegro.devs,brd+'_Allegro_devs.txt')
            if Brd.filetype == 'Altium':
                dumpStruct(Brd, Brd.Altium.nets, brd+'_Altium_nets.txt')
                dumpStruct(Brd, Brd.Altium.refs, brd+'_Altium_refs.txt')
                dumpStruct(Brd, Brd.Altium.devs, brd+'_Altium_devs.txt')
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
'''
Now lets study the components by their pin count.
Given a pin count, return a list of components
'''
#print(json.dumps(A.pinCount, indent=2)); exit(1)
#print(json.dumps(B.pinCount, indent=2)); exit(1)

if listPinCountGroups:
    A_pins = list(A.pinCount.keys()); A_pins.reverse()
    B_pins = list(B.pinCount.keys()); B_pins.reverse()
    comm = P.commonPins
    print('Brd A pin count groups:\n  %s'%str(A_pins).replace(' ',''))
    print('Brd B pin count groups:\n  %s'%str(B_pins).replace(' ',''))
    print('\nPin count groups common to A & B:\n  %s'%str(comm).replace(' ',''))
    print('  %d groups total'%len(comm))
    exit(0)

###############
'''
Make a list of pin count and number of components with that pincount
'''
#print(json.dumps(A.likeRefs, indent=2)); exit(1)
#print(json.dumps(B.likeRefs, indent=2)); exit(1)

if False:  # if you want this output, set this to True
    for numPins,numRefs in A.likeRefs.items():
        print('Number pins: %4d Number parts: %d'%(numPins,numRefs))
    for numPins,numRefs in B.likeRefs.items():
        print('Number pins: %4d Number parts: %d'%(numPins,numRefs))
    exit(0)

#######################################################################
#######################################################################
'''
Make a list of pin counts. Just a simple list
Necessary study info for the block following
'''
#print(json.dumps(P.allPins, indent=2)); exit(1)

if defined(rptFormat):
    '''
    Create a pin count report. We can see the differences between board A and B
    '''
    P.reportPinCounts(ext=rptFormat)  # pass string param, 'CSV' or 'TXT'
    exit(0)

#######################################################################
#######################################################################
'''
Start the hetrogeneous, abstracted netlist compare
'''

# We can specify the pin counts of interest, or use all common pin counts:
#PinsList = [2912,1310,484,101,78,65]  # parts, referenced by pinCount
PinsList = P.commonPins
P.PinsList = PinsList

# How many from that pin count list shall we examine?
P.numPnsList = numPnsList

'''
Make a dict where each pin count points to a list of the refdes with those pincounts
'''
#print(json.dumps(P.refdesByPincount(), indent=2)); exit(1)

###############
'''
Lets try matching refdes.pins between boards.
If a net appears in one board and not the other, flag it for follow-up
'''
# Dump the pin properties list of parts in PartList
#print('\n'.join(B.reportPinProperties(NewPinsList))); exit(1)

###############
###############
###############
# We do some higher level checking, starting below
#

###############
##
if defined(refCompare):
    #print(json.dumps(list(A.byRef.keys()), indent=2)); exit(1)
    #print(json.dumps(list(B.byRef.keys()), indent=2)); exit(1)
    #P.checkPin2PinAtRefdes(Refs[0][0],Refs[0][1],Refs[1][0],Refs[1][1])
    # Lastly, dump the Report Notes, a list of notes made during net-in and checking:
    #exit( P.reportNotes() )
    
    print('at EquatePin2PinConnections')
    #P.EquatePin2PinConnections('A','U5E1','B','CPU1')
    P.EquatePin2PinConnections(Refs[0][0],Refs[0][1],Refs[1][0],Refs[1][1])
    P.reportNetsNotes()
    P.reportPwrNotes()
    P.reportNotes()
    exit(0)

###############
##
# Check the nets connected to parts in PinsList
P.checkNetNames()  # this runs EquateNetNames

# Lastly, dump the Report Notes, a list of notes made during net-in and checking:
result = P.reportNotes()

exit(result)
