name = "netComp.py"

# -*- coding: utf-8 -*-
"""
Created on Thu Mar 14 2019

@author: mlgkschm
"""

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
from sys import exit,argv
import json
import csv
#import time
import re
#import os
#import subprocess
from Local import *  # atoi, defined, mkType, readFile
from os.path import isfile,exists,basename
from sortedcontainers import SortedDict # 
from collections import deque,OrderedDict # 

#
#######################################################################
# useful routines

def getFileType(root):
    exts = ['pstxnet.dat','cpn_rep.rpt','.NET']
    for ext in exts:
        fname = isFileHere(root,ext)
        if defined(fname):
            with open(fname, 'r') as f:
                hdr = f.readline()
            #f.close()
            found = re.search('^Component',hdr)
            if found:
                return('Allegro')
            found = re.search('^FILE_TYPE',hdr)
            if found:
                return('OrCad')
            found = re.search('OrCAD PCB II Netlist Format',hdr)
            if found:
                return('Altium')
    print('ERROR: Cannot find file with root "%s"'%root); exit(1)

def isFileHere(root,ext):
    if len(root):
        if exists('.\\'+root+'_'+ext):
            return(root+'_'+ext)
        elif exists('.\\'+root+ext):
            return(root+ext)
        elif exists('.\\'+root):
            return(root)
    elif exists('.\\'+ext):
            return('.\\'+ext)
    return(None)

def checkFileHere(root,ext,abort=False):
    fname = isFileHere(root,ext)
    if defined(fname):
        return(fname)
    elif abort:
        print('ERROR: Cannot find file "%s"'%root); exit(1)
    else:
        return(None)

def readNetFile(fname):
    s = readFile(fname)
    flines = s.split('\n')
    return(flines)
    
#######################################################################
# netlist input routines (procedural coding meathod)
# note: these reeeeally want to be reorganized as objects

'''
Data structure of readOrcadPstChip output, displayed in JSON format:

{
  "FILE_TYPE": EXPANDEDPARTLIST
  "Comment": Using PSTWRITER 17.2.0 d001Mar-13-2019 at 14:14:44 
  "DATA": {
    "BATTERY_H_SKT_BAT2450_LOTES_BAT": {  # PRIMITIVE name
      "body": {
        "JEDEC_TYPE": "skt_bat2450_lotes",
        "PART_NAME": "BATTERY_H",
        "VALUE": "BATT 2P"
      },
      "pin": {
        "NEG": {
          "PINUSE": "UNSPEC",
          "PIN_NUMBER": "2"
        },
        "POS": {
          "PINUSE": "UNSPEC",
          "PIN_NUMBER": "1"
        }
      }
    }
  }
}
'''
# Read a pstchip.dat file from OrCad netlist generator
def readOrcadPstChip(fname):
    fname = checkFileHere(fname,'pstchip.dat')
    flines = readNetFile(fname)
    #
    primFlag = False; pinFlag = False; bodyFlag = False
    primitive = None; body = None; pin = None; pinProps = None; 
    chips = SortedDict({'DATA': SortedDict()})
    dbg = False; continuance = False
    frag = ''
    lnum = 0
    #
    for l in flines:
        lnum += 1
        if len(l)>0 and l[-1] == '~':
            continuance = True
            frag += l[:-1]
            #print('line %d: line continuation'%lnum)
        elif continuance:
            continuance = False
            l = frag + l
            frag = ''
            #print(l)
        #
        if not continuance:
            if primFlag:
                # We've seen the Primitive flag
                if pinFlag:
                    # We're in the pin field
                    # Pin Name
                    R = re.search(r'^\s+\'(.+)\':',l)
                    if R:
                        pinName = R.group(1)
                        if pinName in pin:
                            print('ERROR: readOrcadPstChip: ',end='')
                            print('Part %s, pin name %s defined more than once'%(primName,pinName))
                        pin[pinName] = SortedDict()
                        pinProps = pin[pinName]
                        if dbg: print('  PIN_NAME:',pinName)
                    # Pin Property
                    R = re.search(r'^\s+([^=]+)=\'([^\']+)\';',l)
                    if R:
                        keywd = R.group(1)
                        val = R.group(2)
                        pinProps[keywd] = val
                        if dbg: print('    %s=%s'%(keywd,val))
                    # End pin
                    R = re.search(r'^\s+end_pin;',l)
                    if R: 
                        # clean up PIN_NUMBER
                        for pinName,pinProps in pin.items():
                            R = re.search(r'\((.+)\)',pinProps['PIN_NUMBER'])
                            pinNums = R.group(1).split(',')
                            pins = []; hetro = False
                            for pinNum in pinNums:
                                if pinNum == '0':
                                    hetro = True
                                else:
                                    pins.append(pinNum)
                            if hetro and len(pins) > 1:
                                print('ERROR: readOrcadPstChip: ',end='')
                                print('Part %s, pin name %s assigned to more than one pin'%(primName,pinName))
                            if len(pins) == 1:
                                pinProps['PIN_NUMBER'] = pins[0]
                            else:
                                pinProps['PIN_NUMBER'] = pins
                        pinFlag = False
                elif bodyFlag:
                    # we're in the body field
                    # Part Property
                    R = re.search(r'^\s+([^=]+)=\'([^\']+)\';',l)
                    if R:
                        keywd = R.group(1)
                        val = R.group(2)
                        body[keywd] = val
                        if dbg: print('    %s=%s'%(keywd,val))
                    # bad line continuation. Detect, report, move on.
                    R = re.search(r'^\S',l)
                    if R:
                        print('Bad line continuation at line %d'%lnum)
                    # End body
                    R = re.search(r'^\s+end_body;',l)
                    if R:
                        body['HETRO'] = hetro
                        bodyFlag = False
                else:
                    # We're in the Primitive field. Look for Pin and Body
                    # Start pin 
                    R = re.search(r'^\s+pin',l)
                    if R:
                        pinFlag = True
                        primitive['PIN'] = SortedDict()
                        pin = primitive['PIN']
                    # Start body
                    R = re.search(r'^\s+body',l)
                    if R:
                        bodyFlag = True
                        primitive['BODY'] = SortedDict()
                        body = primitive['BODY']
                        if dbg: print('  BODY')
                    # End primitive
                    R = re.search(r'^end_primitive;',l)
                    if R:
                        primFlag = False
            else:
                R = re.search(r'^FILE_TYPE=(.+);',l)
                if R:
                    fileType = R.group(1)
                    chips['FILE_TYPE'] = fileType
                    if dbg: print('FILE_TYPE:',fileType)
                    
                R = re.search(r'^{\s*(.+)}',l)
                if R:
                    comment = R.group(1)
                    chips['COMMENT'] = comment
                    if dbg: print('Comment:',comment)

                R = re.search(r'^primitive\s+\'(.+)\'',l)
                if R:
                    primName = R.group(1)
                    primFlag = True
                    chips['DATA'][primName] = SortedDict()
                    primitive = chips['DATA'][primName]
                    if dbg: print('primitive:',primName)
    #print(json.dumps(chips, indent=2)); exit(1)
    return(chips)

'''
Data structure of readOrcadPstChip output, displayed in JSON format:

{
  "FILE_TYPE": EXPANDEDPARTLIST
  "Comment": Using PSTWRITER 17.2.0 d001Mar-13-2019 at 14:14:44 
  "DATA": {
    "A_DIEEDGE_MON1_A_B": {  # NET_NAME
      "CPU1": [  # REFDES
        {
          "PIN_NAME": "DIEEDGE_MON1A_W11",
          "PIN_NUMBER": "W11"
        },
        {
          "PIN_NAME": "DIEEDGE_MON1B_V11",
          "PIN_NUMBER": "V11"
        }
      ]
    },
  }
}
'''
# Read a pstxnet.dat file from OrCad netlist generator
def readOrcadPstXnet(fname):
    fname = checkFileHere(fname,'pstxnet.dat')
    flines = readNetFile(fname)
    netFlag = False; nodeFlag = False
    xnets = SortedDict({
        'NETS': SortedDict(),
        'FILENAME': fname,
    })
    netName = None; nodeName = None; net = None
    dbg = False; continuance = False
    frag = ''
    lnum = 0
    #
    for l in flines:
        lnum += 1
        if len(l)>0 and l[-1] == '~':
            continuance = True
            frag += l[:-1]
            #print('line %d: line continuation'%lnum)
        elif continuance:
            continuance = False
            l = frag + l
            frag = ''
            #print(l)
        #
        if not continuance:
            R_ftyp = re.search(r'^FILE_TYPE\s?=\s?(.+);',l)
            R_comt = re.search(r'^{\s*(.+)}',l)
            R_netn = re.search(r'^NET_NAME',l)
            R_node = re.search(r'^NODE_NAME\s+(.+)\s+(.+)',l)
            R_end  = re.search(r'^END\.',l)
            #
            if R_ftyp:
                fileType = R_ftyp.group(1)
                xnets['FILE_TYPE'] = fileType
                if dbg: print('line %d FILE_TYPE: %s'%(lnum,fileType))
            elif R_comt:
                comment = R_comt.group(1)
                xnets['COMMENT'] = comment
                if dbg: print('line %d Comment: %s'%(lnum,comment))
            elif R_netn:
                lcnt = 0
                netFlag = True; nodeFlag = False
                if dbg: print('line %d NET_NAME'%lnum)
            elif R_node:
                lcnt = 0
                netFlag = False; nodeFlag = True
                nodeRefDes = R_node.group(1)
                nodePinNum = R_node.group(2)
                if dbg: print('line %d NODE_NAME %s %s'%(lnum,nodeRefDes,nodePinNum))
            elif R_end:
                if dbg: print('line %d END.'%lnum)
            #
            elif netFlag:
                lcnt += 1
                if lcnt == 1:
                    R = re.search(r'\'(.+)\'',l)
                    netName = R.group(1)
                    xnets['NETS'][netName] = SortedDict()
                    net = xnets['NETS'][netName]
                    if dbg: print('line %d  %s'%(lnum,netName))
            elif nodeFlag:
                lcnt += 1
                if lcnt == 1:
                    if dbg: print('line %d %s'%(lnum,l))
                if lcnt == 2:
                    R = re.search(r'^\s*\'(.+)\':\s?([^;]*);',l)
                    if R:
                        nodePinNam = R.group(1)
                        if R.group(2):
                            nodeCdsPinId = R.group(2)  # Concept adds this field; OrCad does not.
                    else:
                        print('ERROR pstxnet line %d: re.search returned %s, l=%s'%(lnum,str(R),l))
                        exit(1)
                    if not nodeRefDes in net:
                        net[nodeRefDes] = []  # list of pins
                    node = SortedDict({
                        'PIN_NAME': nodePinNam,
                        'PIN_NUMBER': nodePinNum
                    })
                    net[nodeRefDes].append(node)
                    if dbg: print('line %d  %s'%(lnum,nodePinNam))
    return(xnets)
   
'''
Data structure of readOrcadPstXprt output, displayed in JSON format:

{
  "FILE_TYPE": EXPANDEDPARTLIST
  "Comment": Using PSTWRITER 17.2.0 d001Mar-13-2019 at 14:14:44 
  "DATA": {
    "AC1": {  # REFDES
      "PART_NAME": "C_C0201_220NF",
      "ROOM": "PCIe_DMI_AC",
      "SECTION 1": []
    },
  }
}
'''
# Read a pstxprt.dat file from OrCad netlist generator
def readOrcadPstXprt(fname):
    fname = checkFileHere(fname,'pstxprt.dat')
    flines = readNetFile(fname)
    #
    dirFlag = False; prtFlag = False; roomFlag = False; secFlag = False
    xprt = SortedDict({'DATA': SortedDict()})
    dbg = False; continuance = False
    frag = ''
    lnum = 0
    #
    for l in flines:
        lnum += 1
        if len(l)>0 and l[-1] == '~':
            continuance = True
            frag += l[:-1]
            #print('line %d: line continuation'%lnum)
        elif continuance:
            continuance = False
            l = frag + l
            frag = ''
            #print(l)
        #
        if not continuance:
            R_ftyp = re.search(r'^FILE_TYPE\s*=\s*(.+);',l)
            R_comt = re.search(r'^{\s*(.+)}',l)
            R_drct = re.search(r'^DIRECTIVES',l)
            R_part = re.search(r'^PART_NAME',l)
            R_room = re.search(r'^\s+ROOM=\'(.+)\';',l)
            R_sect = re.search(r'^SECTION_NUMBER\s+(.+)',l)
            R_end  = re.search(r'^END\.',l)
            #
            if R_ftyp:
                fileType = R_ftyp.group(1)
                xprt['FILE_TYPE'] = fileType
                if dbg: print('FILE_TYPE:',fileType)
            elif R_comt:
                comment = R_comt.group(1)
                xprt['COMMENT'] = comment
                if dbg: print('Comment:',comment)
            elif R_drct:
                dirFlag = True; prtFlag = False; roomFlag = False; secFlag = False
                xprt['DATA']['DIRECTIVES'] = SortedDict()
                directives = xprt['DATA']['DIRECTIVES']
            elif R_part:
                lcnt = 0
                dirFlag = False; prtFlag = True; roomFlag = False; secFlag = False
            elif R_room:
                lcnt = 0
                dirFlag = False; prtFlag = False; roomFlag = True; secFlag = False
                roomNum = R_room.group(1)
                part['ROOM'] = roomNum
            elif R_sect:
                lcnt = 0
                dirFlag = False; prtFlag = False; roomFlag = False; secFlag = True
                secNum = R_sect.group(1)
                part['SECTION '+str(secNum)] = []
                section = part['SECTION '+str(secNum)]
            elif R_end:
                if dbg: print('line %d END.'%lnum)
            #
            elif dirFlag:
                R_pstt = re.search(r'^PST_VERSION=\'(.+)\';',l)
                R_root = re.search(r'^ROOT_DRAWING=\'(.+)\';',l)
                R_post = re.search(r'^POST_TIME=\'(.+)\';',l)
                R_sorc = re.search(r'^SOURCE_TOOL=\'(.+)\';',l)
                R_endd = re.search(r'^END_DIRECTIVES;',l)
                # PST_VERSION
                if R_pstt:
                    directives['PST_VERSION'] = R_pstt.group(1)
                # ROOT_DRAWING
                if R_root:
                    directives['ROOT_DRAWING'] = R_root.group(1)
                # POST_TIME
                if R_post:
                    directives['POST_TIME'] = R_post.group(1)
                # SOURCE_TOOL
                if R_sorc:
                    directives['SOURCE_TOOL'] = R_sorc.group(1)
                # End directives
                if R_endd:
                    dirFlag = False  # when uncommented, causes 'else' at end to execute
            elif prtFlag:
                lcnt += 1
                if lcnt == 1:
                    R = re.search(r'^\s+(.+)\s+\'(.+)\':',l)
                    xprt['DATA'][R.group(1)] = SortedDict()
                    part = xprt['DATA'][R.group(1)]
                    part['PART_NAME'] = R.group(2)
            elif roomFlag:
                lcnt += 1
                print('readOrcadPstXprt stuff for \'room\':',l)
                if len(l) == 0:
                    roomFlag = False
            elif secFlag:
                lcnt += 1
                if len(l) > 0:
                    R_sec = re.search(r'^\s+(.*)',l) # add a text scanner. might be useful.
                    if R_sec and len(R_sec.group(1)) > 0:
                        section.append(R_sec.group(1))
                else:
                    secFlag = False
            else: # when nothing else is active...
                if len(l) > 0:  # should only ever be a blank line
                    print('ERROR: readOrcadPstXprt: should never happen, line',lnum)
    return(xprt)
    
###############

'''
Data structure of readOrcadPropExport output, displayed in JSON format:

{
  "DESIGN": "C:\\USERS\\MLGKSCHM\\BOX\\INTERNAL\\PROJECTS\\IN PROGRESS\\ARGO\\_ZEUS_1_CPU\\08_ELECTRICAL_DESIGN\\01_SCHEMATICS\\ZEUS_EVT_ACF_SCH_20190415\\ZEUS_EVT_ACF_SCH_20190415_NETIN.DSN",
  "HEADER": [
    "ID",
    "Part Reference",
    "Value",
    ...,
    "Insert",
    ...,
    "Net Name",
    "Number",
    ...,
    "version"
  ],
  "PARTS": {
    "AC1": {
      ...,
      "Insert": "I",
      ...
    },
    "...": {
    }
  },
  "PINS": {
    "AC1": {
      "1": {
        "AEC_Q": null,
        ...,
      },
      "2": {
        ...,
      }
    },
    "...": {
      ...
    }
  }
}'''
# Read an Orcad part properties export file from OrCad Tools menu
def readOrcadPropExport(fname, pinsToo=False):
    fname = isFileHere(fname,'props.exp')
    #fname = isFileHere(fname,'propsInst.exp')  # "Instance" property export format, prefered
    #fname = checkFileHere(fname,'propsOcc.exp')# "Occurrance" property export format
    #print('Filename',fname);exit(1)
    if not defined(fname):
        return(None)
    flines = readNetFile(fname)
    props = SortedDict({
        'DESIGN': "",
        'HEADER': [],
        'PARTS': SortedDict(),
        'PINS': SortedDict()
    })
    dbg = False
    #
    for l in flines:
        R_desn  = re.search(r'^"DESIGN"\s+"(.+)"',l)
        R_hedr  = re.search(r'^"HEADER"\s+(.*)',l)
        R_partI = re.search(r'^"PARTINST:([^:]+):([^:]+):([^"]+)"\s+(.*)',l)
        R_pinI  = re.search(r'^"PININST:([^:]+):([^:]+):([^:]+):([^"]+)"\s+(.*)',l)
        R_partO = re.search(r'^"PARTOCC:([^"]+)"\s+(.*)',l)
        R_pinO  = re.search(r'^"PINOCC:([^"]+)"\s+(.*)',l)
        R_blank = re.search(r'^\s*$',l)
        #
        if R_desn:
            props['DESIGN'] = R_desn.group(1).replace('"','')
            if dbg: print('DESIGN:',props['DESIGN'])
        elif R_hedr:
            header = R_hedr.group(1).replace('"','').split('\t')
            props['HEADER'] = header
            if dbg: print('HEADER',props['HEADER'])
        elif R_partI:
            readOrcadPropExport_RpartI(props,R_partI,dbg)
        elif R_pinI and pinsToo:
            readOrcadPropExport_RpinI(props,R_pinI,dbg)
        elif R_partO:
            readOrcadPropExport_RpartO(props,R_partO,dbg)
        elif R_pinO and pinsToo:
            readOrcadPropExport_RpinO(props,R_pinO,dbg)
        elif R_blank:
            None
        else:
            print('ERROR: readOrcadPropExp: should not get here')
            print(' line =',l); exit(1)
    return(props)
    
def readOrcadPropExport_RpartI(props,R_partI,dbg=False):
    sheet = R_partI.group(1)
    page = R_partI.group(2)
    partID = R_partI.group(3)
    data = R_partI.group(4).replace('"','').split('\t')
    refdes = data[0]
    if not refdes in props['PARTS']:
        props['PARTS'][refdes] = SortedDict()
    for hdr,fld in zip(props['HEADER'],data):
        if fld == "<null>": fld = None
        props['PARTS'][refdes][hdr] = fld
    if dbg: 
        print('PARTINST "%s","%s","%s"'%(sheet,page,partID))
        print(' DATA %s:'%refdes,end='')
        for hdr in props['HEADER'][:10]:
            print('%s,'%props['PARTS'][refdes][hdr],end='')
        print()

def readOrcadPropExport_RpartO(props,R_partO,dbg=False):
    # partID = R_partO.group(1)
    data = R_partO.group(2).replace('"','').split('\t')
    refdes = data[1]
    if not refdes in props['PARTS']:
        props['PARTS'][refdes] = SortedDict()
    for hdr,fld in zip(props['HEADER'],data):
        if fld == "<null>": fld = None
        props['PARTS'][refdes][hdr] = fld
    #print('\n%s '%refdes,end='')
    if dbg: 
        print('PARTOCC "%s","%s"'%(refdes,partID))
        print(' DATA %s:'%refdes,end='')
        for hdr in props['HEADER']:
            print('%s:%s,'%(hdr,props['PARTS'][refdes][hdr]),end='')
        print()

def readOrcadPropExport_RpinI(props,R_pinI,dbg=False):
    sheet = R_pinI.group(1)
    page = R_pinI.group(2)
    partID = R_pinI.group(3)
    pinID = R_pinI.group(4)
    data = R_pinI.group(5).replace('"','').split('\t')
    #print('data[0]',data[0])
    refdes, pin = data[0].split(':')
    if not refdes in props['PINS']:
        props['PINS'][refdes] = SortedDict()
    if not pin in props['PINS'][refdes]:
        props['PINS'][refdes][pin] = SortedDict()
    for hdr,fld in zip(props['HEADER'],data):
        if fld == "<null>": fld = None
        props['PINS'][refdes][pin][hdr] = fld
    if dbg: 
        print('PININST "%s","%s","%s","%s"'%(sheet,page,partID,pinID))
        print(' DATA %s:'%refdes,end='')
        for hdr in props['HEADER']:
            print('%s,'%props['PINS'][refdes][pin][hdr],end='')
        print()

def readOrcadPropExport_RpinO(props,R_pinO,dbg=False):
    partID = R_pinO.group(1)
    data = R_pinO.group(2).replace('"','').split('\t')
    #
    dataDct = SortedDict()
    for hdr,fld in zip(props['HEADER'],data):
        dataDct[hdr] = fld
    pin = dataDct['Number']
    ##refdes = data[0]  # get it rom the PARTOCC record
    #
    #print('%s, '%pin,end='')
    if not refdes in props['PINS']:
        props['PINS'][refdes] = SortedDict()
    if not pin in props['PINS'][refdes]:
        props['PINS'][refdes][pin] = SortedDict()
    for hdr,fld in zip(props['HEADER'],data):
        if fld == "<null>": fld = None
        props['PINS'][refdes][pin][hdr] = fld
    if dbg: 
        print('PINOCC "%s","%s"'%(refdes,partID))
        print(' DATA %s:'%refdes,end='')
        for hdr in props['HEADER']:
            print('%s,'%props['PINS'][refdes][hdr],end='')
        print()

###############

'''
Data structure of readAllegroNets output, displayed in JSON format:

{
  "FILE_TYPE": EXPANDEDPARTLIST
  "Comment": Using PSTWRITER 17.2.0 d001Mar-13-2019 at 14:14:44 
  "DATA": {
    "A_DIEEDGE_MON1_B_C": {  # NET_NAME
      "U1": [  # REFDES
        {
          "COMP_DEVICE_TYPE": "SKL_S55_EXT_IP_BGA-NA_50448,EMPTY,SKL_S55_EXT_IP,0.12,LPDB,GENERIC",
          "PIN_NAME": "DIEEDGE_MON1B_U11",
          "PIN_NUMBER": "U11",
          "PIN_TYPE": "BI"
        },
        {
          "COMP_DEVICE_TYPE": "SKL_S55_EXT_IP_BGA-NA_50448,EMPTY,SKL_S55_EXT_IP,0.12,LPDB,GENERIC",
          "PIN_NAME": "DIEEDGE_MON1C_U12",
          "PIN_NUMBER": "U12",
          "PIN_TYPE": "BI"
        }
      ]
    },
  }
}
'''
# Read a cpn_rep.rpt file from Allegro report generator
def readAllegroNets(fname):
    fname = checkFileHere(fname,'cpn_rep.rpt')
    # assume it can be read as a CSV file, which it can, for the most part
    def incDefName(last):
        # Found a non-named net? Give it a generic name
        next = last+1
        name = 'N'+'%05d'%next
        return(name)
    #
    cpnRep = []
    defNName = 0
    with open(fname, 'r') as f:
        sread = csv.reader(f)  # assume it's a CSV format file
        for row in sread:
            cpnRep.append(row)
    #f.close()
    #
    info = [cpnRep[i][0] for i in range(3)]  # grab a copy of the info rows
    cpnRep = cpnRep[4:]  # then remove the useless info rows
    header = cpnRep.pop(0)  # pop the header, with all the field names
    nname_hdr = header.pop()  # and the NET_NAME from the header
    #
    Devs = SortedDict()
    byNet = SortedDict({
        'INFO': info, 
        'FILENAME': fname,
        'NETS': SortedDict()
    })  # create the NETS section
    Nets = byNet['NETS']  # and get a pointer to it
    #
    for rowLst in cpnRep:  # scan through each row of the netlist file
        netName = rowLst.pop()  # pop off the NET_NAME
        netName = netName if len(netName) > 0 else incDefName(defNName)  # <defaults>
        if not netName in Nets:
            Nets[netName] = SortedDict()  # create entry for new netName
        #
        pin = SortedDict()  # make a pin registry
        for fldName,fldVal in zip(header,rowLst):
            if fldName == 'COMP_DEVICE_TYPE':
                comp_device_type = fldVal  # copy the data for this row (i.e. refdes/pin)
            if fldName == 'REFDES':
                refdes = fldVal
            else:
                pin[fldName] = fldVal
        if not refdes in Devs:
            Devs[refdes] = comp_device_type
        if not refdes in Nets[netName]:
            Nets[netName][refdes] = []  # make sure there's an entry for this refdes
        Nets[netName][refdes].append(pin)  # add the pin to NET_NAME
    #
    Allegro = mkType('Net')
    Allegro.nets = byNet
    Allegro.refs = None
    Allegro.devs = Devs
    return(Allegro)

###############

'''
Data structure of readAltiumNets output, displayed in JSON format:

[  # returns an array...
  {  # "nets" structure
    "FILE_TYPE": EXPANDEDPARTLIST
    "Comment": Using PSTWRITER 17.2.0 d001Mar-13-2019 at 14:14:44 
    "DATA": {
      "A_DIEEDGE_MON1_B_C": {  # NET_NAME
        "U1": [  # REFDES
          {
            "COMP_DEVICE_TYPE": "SKL_S55_EXT_IP_BGA-NA_50448,EMPTY,SKL_S55_EXT_IP,0.12,LPDB,GENERIC",
            "PIN_NAME": "DIEEDGE_MON1B_U11",
            "PIN_NUMBER": "U11",
            "PIN_TYPE": "BI"
          },
          {
            "COMP_DEVICE_TYPE": "SKL_S55_EXT_IP_BGA-NA_50448,EMPTY,SKL_S55_EXT_IP,0.12,LPDB,GENERIC",
            "PIN_NAME": "DIEEDGE_MON1C_U12",
            "PIN_NUMBER": "U12",
            "PIN_TYPE": "BI"
          }
        ]
      },
    }
  },
  {  # "refs" structure
    "D1": {  # REFDES
      "A": {  # PIN_NUMBER
        "NET": "P3V3_PCH",
        "PIN_NAME": "A"
      },
      "C": {
        "NET": "P3V3_RTC",
        "PIN_NAME": "C"
      }
    },
    ...
  },
  {  # device data structure
    "BU401": {  # REFDES
      "PART_NAME": "MICRO-USB-SMT-TH",
      "VALUE": "Micro USB"
    },
    "C201": {  # REFDES
      "PART_NAME": "0603",
      "VALUE": "10pF"
    },
    ...
  }
]
'''
# Read a net_rep.rpt file from Allegro report generator
def readAltiumNets(fname):
    fname = checkFileHere(fname,'.NET')
    flines = readNetFile(fname)
    #print('#flines:\n%s'%'\n'.join(flines))
    #
    byNet = SortedDict({  
        'NETS':SortedDict()  
    })
    nets = byNet['NETS']
    refs = SortedDict()
    devs = SortedDict()
    #
    level = 0
    #
    for line in flines:
        #print('#line:',line);
        d_open  = re.search('^\s*\(',line)
        d_close = re.search('\)\s*$',line)
        r_data = re.search('\(\s+([^\)]+)',line)
        if d_open:
            #print('%(',d_open.group(0))
            level += 1
        if r_data:
            n_data = re.search('(.*)\s$',r_data.group(1))
            data = n_data.group(1) if n_data else r_data.group(1)
            #print('"%s"'%data)
            #
            if level == 1:
                byNet['FILE_TYPE'] = data
            if level == 2:
                node = re.search('(\S+)\s(\S+)\s(\S+)(\s(.+))?$',data)
                netNum = node.group(1)
                partName = node.group(2)
                refDes = node.group(3)
                value = node.group(5)
                if refDes in refs:
                    print('ERROR: should never get here'); exit(1)
                refs[refDes] = SortedDict()
                if refDes in devs:
                    print('ERROR: should never get here'); exit(1)
                devs[refDes] = SortedDict({ 
                    'PART_NAME': partName, 
                    'VALUE': value 
                })
            if level == 3:
                node = re.search('(\S+)\s(\S+)',data)
                pinNum = node.group(1)
                netName = node.group(2)
                refs[refDes][pinNum] = SortedDict({ 
                    'NET':netName, 
                    'PIN_NAME':None 
                })
                if not netName in nets:
                    nets[netName] = SortedDict()
                if not refDes in nets[netName]:
                    nets[netName][refDes] = []
                nets[netName][refDes].append(SortedDict({ 
                    'PIN_NUMBER':pinNum, 
                    'PIN_NAME': None 
                }))
        if d_close:
            # if level == 1:
                # print(INFO)
            # if level == 2:
                # print('%s,%s,%s,%s'%(netNum,partName,refDes,value))
            # if level == 3:
                # print('%s,%s'%(pinNum,netName))
            level -= 1
    #
    #print(json.dumps(refs, indent=2)); exit(1)
    #print(json.dumps(nets, indent=2)); exit(1)
    #print(json.dumps(devs, indent=2)); exit(1)
    #
    Altium = mkType('Net')
    Altium.nets = byNet
    Altium.refs = refs
    Altium.devs = devs
    return(Altium)
    
#####################

'''
Data structure of getNameValueOrcad output, displayed in JSON format:

{
  "Y8B1": {  # REFDES
    "PART_NAME": "OSC_4P_A_SM-J70888-001",
    "VALUE": "24MHZ"
  }
}
'''
def getNameValueOrcad(h):  # byRef,xprts,chips):
    # Routine for OrCad netins
    byRef = h.byRef
    xprts = h.Orcad.xprts['DATA']
    chips = h.Orcad.chips['DATA']
    #
    RefDes = SortedDict()
    PartValues = {}
    for ref in byRef.keys():
        partName = xprts[ref]['PART_NAME']
        value = chips[partName]['BODY']['VALUE']
        if not partName in PartValues:
            PartValues[partName] = SortedDict({  
                'PART_NAME': partName,  
                'PART_TYPE': "",  
                'VALUE': value  
            })
        RefDes[ref] = PartValues[partName]
    return(RefDes)

'''
Data structure of getNameValueAllegro output, displayed in JSON format:

{
  "Y8B1": {  # REFDES
    "COMP_DEVICE_TYPE": "OSC_4P_A_SM-J70888-001,OSC,24MHZ,25PPM,LPDB,GENERIC",
    "PART_NAME": "OSC_4P_A_SM-J70888-001",
    "VALUE": "24MHZ"
  }
}
'''
def getNameValueAllegro(h):  # byRef,byNet):
    # Routine for Allegro .brd netins
    byNet = h.byNet
    RefDes= SortedDict(); PartValues = {}
    for net in byNet.keys():
        for ref in byNet[net].keys():
            for pin in byNet[net][ref]:
                comp_device_type = pin['COMP_DEVICE_TYPE'].split(',')
                partName = ''; partType = ''; value = ''
                try:
                    partName = comp_device_type[0]
                    partType = comp_device_type[1]
                    value = comp_device_type[2]
                except IndexError:
                    None  # sometimes there's no VALUE, i.e., comp_device_type[2]
                if not ref in RefDes:
                    if not partName in PartValues:
                        PartValues[partName] = SortedDict({  
                            'COMP_DEVICE_TYPE': pin['COMP_DEVICE_TYPE'],  
                            'PART_NAME': partName,  
                            'PART_TYPE': partType,  
                            'VALUE': value  
                        })
                    RefDes[ref] = PartValues[partName]
    return(RefDes)

'''
Data structure of getNameValueOrcad output, displayed in JSON format:

{
  "Y8B1": {  # REFDES
    "PART_NAME": "OSC_4P_A_SM-J70888-001",
    "VALUE": "24MHZ"
  }
}
'''
def getNameValueAltium(h):  # 
    # Routine for OrCad netins
    nets = h.Altium.nets['NETS']
    refs = h.Altium.refs
    devs = h.Altium.devs
    #
    #print('Altium nets\n%s'%json.dumps(nets, indent=2)); exit(1)
    #print('Altium refs\n%s'%json.dumps(refs, indent=2)); exit(1)
    #print('Altium devs\n%s'%json.dumps(devs, indent=2)); exit(1)
    return(h.Altium.devs)

###############
# OrCad netlists come in three files.
# Read them all with one procedure call:
def readOrcadNets(fname):
    Orcad = mkType('Net')
    Orcad.chips = readOrcadPstChip(fname)
    #print(json.dumps(Orcad.chips, indent=2)); exit(1)
    Orcad.xnets = readOrcadPstXnet(fname)
    #print(json.dumps(Orcad.xnets, indent=2)); exit(1)
    Orcad.xprts = readOrcadPstXprt(fname)
    #print(json.dumps(Orcad.xprts, indent=2)); exit(1)
    Orcad.props = readOrcadPropExport(fname)
    #print(json.dumps(Orcad.props, indent=2)); exit(1)
    #
    return(Orcad)

def addOrcadProps(self):
    if defined(self.Orcad.props):
        props = self.Orcad.props['PARTS']
        parts = self.Orcad.chips['DATA']
        Devs  = self._Devs
        Refs  = self._Refs
        #
        self.empty = []
        for ref,propDct in props.items():
            if propDct['insert'] is not 'I':
                self.empty.append(ref)

##############################################################################
# An object to represent netlists. Understands both OrCad and Allegro netlist files
class Netlist:
    type = 'Netlist'  # type = Netlist
    def __init__(self,filename="",filetype=None):
        self._filename = filename
        self._filetype = filetype
        self._brdID = filename  # this is set by twoLists
        self._byRef = None
        self._byNet = None
        self._byXnet = None
        self._Devs = None
        self._Refs = None
        self._Xnets = None
        self._XnetXref = None
        self._refDes = None
        self._flatNet = None
        self._flatXnet = None
        #
        self._pinCnt = None
        self._likeRefs = None
        self._numPins = None
        self._valueByRef = None
        self._powerNets = None
        self._groundNets = None
        self._NoConnectList = None
        self._IgnoreList = None
        self._ConnectorList = None
        self._PwrGndAdded = None
        self._Actives = None
        #
        self.Orcad = None   # mkType('Net')
        self.Allegro = None # mkType('Net')
        self.Altium = None  # mkType('Net')
        #
        self.ftypes = ['OrCad','Allegro','Altium']  # We understand these types of netlists
        self.fixPinType = {'BI':'BI', 'IN':'IN', 'OUT':'OUT', 'OCA':'OUT', 'OCL':'OUT', 
            'NC':'NC', 'POWER':'POWER', 'GROUND':'GROUND', 'UNSPEC':'UNSPEC'}
    
    @property
    def nick(self):
        return(self._brdID)
    
    @property
    def filename(self):
        return(self._filename)
    @filename.setter
    def filename(self,fname):
        self._filename = fname
    
    @property
    def filetype(self):
        if not defined(self._filetype):
            self._filetype = getFileType(self._filename)
        return(self._filetype)
    @filetype.setter
    def filetype(self,ftype):
        self._filetype = ftype

    @property
    def maxPins(self):
        if not defined(self._byNet):
            self.readNetlist()
        return(max(self._pinCnt))
    
    '''
    See "readAllegroNets" or "readOrcadNets" for data structure of byNet
    '''
    @property
    def byNet(self,net=None,ref=None):
        if not defined(self._byNet):
            self.readNetlist()
        if defined(net):
            if defined(ref):
                return(self._byNet[net][ref])
            else:
                return(self._byNet[net])
        else:
            return(self._byNet)
    
    '''
    See ...
    '''
    @property
    def byXnet(self,net=None,ref=None):
        if not defined(self._byXnet):
            self._byXnet, self._XnetXref = self.makeByXnet()
        if defined(net):
            if defined(ref):
                return(self._byXnet[net][ref])
            else:
                return(self._byXnet[net])
        else:
            return(self._byXnet)
    
    '''
    See "net2ref" for data structure of byRef
    '''
    @property
    def byRef(self,ref=None,pin=None):
        if not defined(self._byRef):
            self.net2ref()
        if defined(ref):
            if defined(pin):
                return(self._byRef[ref][pin])
            else:
                return(self._byRef[ref])
        else:
            return(self._byRef)
    
    '''
    See ... for data structure of ...
    '''
    @property
    def Devs(self,name=None,pin=None):
        if not defined(self._byNet):
            self.readNetlist()
        if defined(name):
            if defined(pin):
                return(self._Devs[name][pin])
            else:
                return(self._Devs[name])
        else:
            return(self._Devs)
    
    '''
    See ... for data structure of ...
    '''
    @property
    def Refs(self,ref=None):
        if not defined(self._byNet):
            self.readNetlist()
        if defined(ref):
            return(self._Refs[ref])
        else:
            return(self._Refs)
    
    @property
    def Nets(self):
        nets = list(self.byNet.keys())
        return(sorted(nets))
    
    @property
    def XnetXref(self):
        if not defined(self._XnetXref):
            self._byXnet, self._XnetXref = self.makeByXnet()
        return(self._XnetXref)
    
    @property
    def Xnets(self):
        if not defined(self._Xnets):
            self._Xnets = self.findXnets()
        return(self._Xnets)

    '''
    See "getNameValueOrcad" or "getNameValueAllegro" for data structure of RefDes
    '''
    @property
    def RefDes(self):
        if not defined(self._refDes):
            self.byNet  # make sure the netlist has been read
            if self.checkFiletype() == 'OrCad':
                self._refDes = getNameValueOrcad(self)
            elif self.checkFiletype() == 'Allegro':
                self._refDes = getNameValueAllegro(self)
            elif self.checkFiletype() == 'Altium':
                self._refDes = getNameValueAltium(self)
            else:
                print('ERROR: RefDes: should never happen'); exit(1)
        return(self._refDes)
    
    '''
    Data structure of pinCount, displayed in JSON format:
    {
      "<Pin count>": [  # Second to max pincount found
        "<RefDes>",  # Refdes list
        "<RefDes>"
      ],
      "<Pin count>": [  # Max pincount found
        "<RefDes>",
        "<RefDes>"
      ]
    }
    '''
    @property
    def pinCount(self):
        if not defined(self._pinCnt):
            byRef = self.byRef.copy()
            pinCnt = SortedDict()
            for ref,pins in byRef.items():
                numPins = len(pins)
                if not numPins in pinCnt:
                    pinCnt[numPins] = []
                pinCnt[numPins].append(ref)
            self._pinCnt = pinCnt
        #print(json.dumps(pinCnt, indent=2)); exit(1)
        return(self._pinCnt)
    
    '''
    Data structure of likeRefs, displayed in JSON format:
    {
      "<pinCount X>": <number of refdes with pinCount = X>,
      "<pinCount Y>": <number of refdes with pinCount = Y>
    }
    '''
    @property
    def likeRefs(self):
        if not defined(self._likeRefs):
            self._likeRefs = SortedDict()
            for numPins,refs in self.pinCount.items():
                self._likeRefs[numPins] = len(refs)
        return(self._likeRefs)
    
    @property
    def flatNet(self):
        if not defined(self._flatNet):
            self._flatNet = self.makeFlatByNet(useX=False)
        return(self._flatNet)
    
    @property
    def flatXnet(self):
        if not defined(self._flatXnet):
            self._flatXnet = self.makeFlatByNet(useX=True)
        return(self._flatXnet)
    
    def makeFlatByNet(self,useX=False):
        if useX:
            netlist = self.byXnet.copy()
            isFlatNet = defined(self._flatXnet)
            flatNet = self._flatXnet
            name = 'flatXnet'
        else:
            #print('X M_A_ALERT_N',json.dumps(self.byNet['M_A_ALERT_N'], indent=2)); #exit(1)
            netlist = self.byNet.copy()
            isFlatNet = defined(self._flatNet)
            flatNet = self._flatNet
            name = 'flatNet'
        #
        # if self.nick == 'B' and name == 'flatNet':
            # #print('M_A_ALERT_N',netlist['M_A_ALERT_N'])
            # print('1 M_A_ALERT_N',json.dumps(netlist['M_A_ALERT_N'], indent=2)); #exit(1)
        if not isFlatNet:
            flatNet = SortedDict()
            for net,refsDct in netlist.items():
                for ref,pinsLst in refsDct.items():
                    for pin in pinsLst:
                        # if ref == 'R1246' and name == 'flatNet':
                            # print('%s:'%name,'net=%s'%net,'ref=%s'%ref,'pins=%s\n'%pinsLst)
                            # print('%s:'%name,'pins=%s\n'%refsDct['R1246'])
                            # print('%s:'%name,'json=%s\n'%json.dumps(refsDct['R1246'], indent=2))
                            # print('%s:'%name,'json=%s'%json.dumps(refsDct, indent=2))
                            # raise NameError('R1246')
                        if not net in flatNet:
                            flatNet[net] = []
                        flatNet[net].append('%s.%s'%(ref,pin['PIN_NUMBER']))
        return(flatNet)
    
    @property
    def Actives(self):
        if not defined(self._Actives):
            self._Actives = []
        return(self._Actives)
    @Actives.setter
    def Actives(self,ActivesLst):
        if isinstance(ActivesLst,list):
            self._Actives = ActivesLst
            if not self.checkActives():
                print('WARNING: Brd %s: Actives has stale value(s)'%self.nick)
        else:
            print('ERROR: Actives: Stored object must be type List'); exit(1)
        return(self._Actives)
    
    @property
    def NoConnectList(self):
        if not defined(self._NoConnectList):
            self._NoConnectList = []
        return(self._NoConnectList)
    @NoConnectList.setter
    def NoConnectList(self,NoConnectLst):
        if isinstance(NoConnectLst,list):
            self._NoConnectList = NoConnectLst
            if not self.checkNoConnectList():
                print('WARNING: Brd %s: NoConnectLst has stale value(s)'%self.nick)
        else:
            print('ERROR: NoConnectList: Stored object must be type List'); exit(1)
    
    @property
    def IgnoreList(self):
        if not defined(self._IgnoreList):
            self._IgnoreList = []
        return(self._IgnoreList)
    @IgnoreList.setter
    def IgnoreList(self,IgnoreLst):
        if isinstance(IgnoreLst,list):
            self._IgnoreList = IgnoreLst
            if not self.checkIgnoreList():
                print('WARNING: Brd %s: IgnoreLst has stale value(s)'%self.nick)
        else:
            print('ERROR: IgnoreList: Stored object must be type List'); exit(1)
    
    @property
    def ConnectorList(self):
        if not defined(self._ConnectorList):
            self._ConnectorList = []
        return(self._ConnectorList)
    @ConnectorList.setter
    def ConnectorList(self,ConnLst):
        if isinstance(ConnLst,list):
            self._ConnectorList = ConnLst
            if not self.checkConnectorList():
                print('WARNING: Brd %s: ConnectorList has stale value(s)'%self.nick)
        else:
            print('ERROR: ConnectorList: Stored object must be type List'); exit(1)
    
    @property
    def PwrGndAdded(self):
        if not defined(self._PwrGndAdded):
            self._PwrGndAdded = []
        return(self._PwrGndAdded)
    @PwrGndAdded.setter
    def PwrGndAdded(self,PwrGndLst):
        if isinstance(PwrGndLst,list):
            self._PwrGndAdded = PwrGndLst
            if not self.checkPwrGndAdded():
                print('WARNING: Brd %s: PwrGndAdded has stale value(s)'%self.nick)
        else:
            print('ERROR: PwrGndAdded: Stored object must be type List'); exit(1)
    
    
    @property
    def PowerNets(self):
        if not defined(self._powerNets):
            self.findPowerNets()
        return(self._powerNets)
    @PowerNets.setter
    def PowerNets(self,net):
        if isinstance(net, list):
            if not defined(self._powerNets):
                self._powerNets = net
            else:
                self._powerNets.extend(net)
        else:
            if not defined(self._powerNets):
                self._powerNets = [net]
            else:
                self._powerNets.append(net)
        if not self.checkActives():
            print('WARNING: Brd %s: Actives has stale value(s)'%self.nick)
    
    @property
    def GroundNets(self):
        if not defined(self._groundNets):
            self._groundNets = []
        return(self._groundNets)
    @GroundNets.setter
    def GroundNets(self,net):
        if isinstance(net, list):
            if not defined(self._groundNets):
                self._groundNets = net
            else:
                self._groundNets.extend(net)
        else:
            if not defined(self._groundNets):
                self._groundNets = [net]
            else:
                self._groundNets.append(net)
    
    def getDevName(self,ref):
        if not defined(self._byNet):
            self.readNetlist()
        return(self.Refs[ref])
        
    def getDevice(self,name):
        if not defined(self._byNet):
            self.readNetlist()
        return(self.Devs[name])
    
    def getDevByRef(self,ref):
        return(self.getDevice(self.getDevName(ref)))
    
    def getValByRef(self,ref):
        return(self.getDevByRef(ref)['PART']['VALUE'])
    
    def getPinsByRef(self,ref):
        return(self.getDevByRef(ref)['PINS'])
    
    def getNameByRef(self,ref):
        return(self.getDevByRef(ref)['PART']['PART_NAME'])
    
    def getPinType(self,Ref,Pin):
        if defined(self._Devs) and defined(self._Refs):
            try:
                type = self.Devs[self.Refs[Ref]]['PINS'][Pin]['PIN_TYPE']
            except KeyError as e:
                print('ERROR: getPinType: KeyError exception:',str(e))
                print('Brd=%s Ref=%s Pin=%s'%(self.nick,Ref,Pin))
                print('Dev=%s'%self.Refs[Ref])
                print('Device \'PART\'',json.dumps(self.Devs[self.Refs[Ref]]['PART'], indent=2))
                print('Device \'PINS\'',json.dumps(list(self.Devs[self.Refs[Ref]]['PINS'].keys()), indent=2))
                exit(1)
            return(type)
        else:
            #print('WARNING: getPinType: undefined attribute')
            return("")

    def findPowerNets(self):
        byNet = self.byNet.copy()
        pwrsLst = SortedDict()
        senseList = ['VSENSE_','_VSENSE','SENSE_','_SENSE']
        #
        for net in self.PwrGndAdded:
            pwrsLst[net] = 'POWER'
        #
        for net,refsDat in byNet.items():
            for ref,pinsLst in refsDat.items():
                for pinDct in pinsLst:
                    pin = pinDct['PIN_NUMBER']
                    if self.getPinType(ref,pin) in ['POWER','GROUND']:
                        snsWord = 0
                        for word in senseList:
                            if word in net:
                                snsWord |= 1
                        if not snsWord:
                            pwrsLst[net] = self.getPinType(ref,pin)
        self._powerNets = list(pwrsLst.keys())
        if 'GND' in self._powerNets:
            self.GroundNets = 'GND'
        return(self._powerNets)
    
    '''
    This method will tell you what's on the other side of a DC blocking cap
    '''
    def getOtherPinNet(self,Ref,Pin):
        pinsDct = self.byRef[Ref]
        pins = pinsDct.copy()
        del pins[Pin]
        nets = []
        for pin,propDct in pins.items():
            nets.append(propDct['NET'])
        if len(nets) > 1:
            print('ERROR: getOtherPinNet: should never happen')
            print('Ref %s, Pin %s, nets %s'%(str(Ref),str(Pin),str(nets)))
            nets[0]=None
            #exit(1)
        return(nets[0])
    
#################
    def isPowerNet(self,net):
        if not defined(self._powerNets):
            self.findPowerNets()
        return(net in self._powerNets)
        
    def isGroundNet(self,net):
        if not defined(self._groundNets):
            self.findPowerNets()
        return(net in self._groundNets)
        
    def isNoConnectNet(self,net):
        if not defined(self._NoConnectList):
            self._NoConnectList = []
        return(net in self._NoConnectList)
    
    def isIgnoreNet(self,net):
        if not defined(self._IgnoreList):
            self._IgnoreList = []
        return(net in self._IgnoreList)
    
    '''
    Ever wonder if the part you're holding is a passive resistor or capacitor?
    '''
    def isPassive(self,Ref):
        try:
            primName = self.Refs[Ref]
        except TypeError as e:
            print('Error:',e)
            print('Ref=%s'%Ref)
            if not defined(self.Refs): print('self.Refs=%s'%str(self.Refs))
            exit(1)
        partProps = self.Devs[primName]
        partPins = list(partProps['PINS'].keys())
        #partName = partProps[partPins[0]]['PART_NAME']
        partName = primName
        #print('partName',partName,'partPins',partPins)
        #
        pinCnt = len(partPins)
        if pinCnt != 2:
            #print('isPassive 1',partName,pinCnt)
            return(False)
        #
        passives = ['CAP','RES','C_C','R_R']
        if partName[:3] in passives:
            return(True)
        else:
            #print('isPassive 2',partName)
            return(False)
    
    '''
    Given a refdes Ref, and a pin Pin, is the other side a power rail?
    '''
    def isPullUpDown(self,Ref):
        pins = self.byRef[Ref]
        if len(pins) == 2:
            for pin,props in pins.items():
                if self.isPowerNet(props['NET']):
                    return(True)
        return(False)
    
    '''
    Given a refdes Ref, and a pin Pin, is the other side a power rail?
    '''
    def isPullDown(self,Ref):
        pins = self.byRef[Ref]
        if len(pins) == 2:
            for pin,props in pins.items():
                if self.isGroundNet(props['NET']):
                    return(True)
        return(False)
    
    def isXnet(self,Net):
        return(Net in self.Xnets)
    
    def toXnet(self,Net):
        if self.isXnet(Net):
            Net = self.XnetXref[Net]
        return(Net)
        
#########################
    '''
    Given a net Net1, start from source refdes sRef, is this an extended net, Xnet?
    '''
    def findXnets(self):
        Xnets = SortedDict()
        #
        byNet = self.byNet.copy()
        byRef = self.byRef.copy()
        #
        for Net1,refsDct in byNet.items():
            if not self.isPowerNet(Net1):
                if not Net1 in Xnets:
                    #
                    refLst = []
                    extNet = []
                    passive = False
                    #
                    for ref1,pins1Lst in byNet[Net1].items():
                        if self.isPassive(ref1):
                            if len(pins1Lst) == 1:
                                if not self.isPullUpDown(ref1):
                                    pin1 = pins1Lst[0]['PIN_NUMBER']
                                    Net2 = self.getOtherPinNet(ref1,pin1)
                                    #
                                    ## I need to see an active device on the other net
                                    foundActive = False
                                    for ref2,pins2Lst in byNet[Net2].items():
                                        if not self.isPassive(ref2):
                                            foundActive = True
                                    ## If we found an active device, then this is an Xnet
                                    if foundActive:
                                        extNet.append(Net2)
                    #
                    if len(extNet) == 1 and foundActive:
                        Net2 = extNet[0]
                        Xnets[Net1] = Net2
                        Xnets[Net2] = Net1
        #
        return(Xnets)
    
    def makeByXnet(self):
        byNet = self.byNet.copy()
        Xnets = self.Xnets.copy()
        byXnet = SortedDict()
        XnetXref = SortedDict()
        D = '#'  # D means "Delimiter"
        #
        doneNets = []
        for netName,refDct in byNet.items():
            if not netName in doneNets:
                if  netName in Xnets:
                    net1 = netName
                    net2 = Xnets[netName]
                    xnet = net1+D+net2
                    XnetXref[net1] = xnet
                    XnetXref[net2] = xnet
                    #
                    if xnet in byXnet:
                        print('ERROR: makeByXnet: should not happen'); exit(1)
                    byXnet[xnet] = SortedDict()
                    for ref,pinsLst in byNet[net1].items():
                        byXnet[xnet][ref] = pinsLst.copy()
                    for ref,pinsLst in byNet[net2].items():
                        if ref in byXnet[xnet]:
                            byXnet[xnet][ref].extend(pinsLst)
                        else:
                            byXnet[xnet][ref] = pinsLst.copy()
                    #
                    doneNets.extend([net1,net2])
                else:
                    byXnet[netName] = refDct.copy()
        return([byXnet, XnetXref])
    
######################
    def getAllegroDevs(self):
        #byNet = self.byNet.copy()
        byNet = self.Allegro.nets['NETS'].copy()  # We're deleting stuff, so make a copy
        devs = self.Allegro.devs.copy()
        Devs = SortedDict()
        Refs = SortedDict()
        #
        for ref,cdt in devs.items():
            comp_device_type = cdt.split(',')
            primName = ''; partType3 = ''; value = ''
            try:
                primName = comp_device_type[0]
                partType3 = comp_device_type[1]
                value = comp_device_type[2]
            except IndexError:
                None  # sometimes there's no VALUE, i.e., comp_device_type[2]
            #
            if primName.find('_') != -1:
                partType = primName[:primName.find('_')]
            else:
                partType = partType3
            #
            if not primName in Devs:
                Devs[primName] = SortedDict({  
                    'PINS': SortedDict(),  
                    'PART': SortedDict()  
                })
            device = Devs[primName]['PART']
            device['COMP_DEVICE_TYPE'] = cdt
            device['PART_NAME'] = primName  # ya, its redundant, but in OrCad nets its not
            device['PART_TYPE'] = partType
            device['PART_TYPE2'] = partType3+'_'+partType
            device['PART_TYPE3'] = partType3
            device['VALUE'] = value
            #
            Refs[ref] = primName;
        #
        for net,refsDct in byNet.items():
            for ref,pinsLst in refsDct.items():
                primName = Refs[ref]
                #
                for pinDct in pinsLst:
                    pin = SortedDict()
                    for propNm,propVl in pinDct.items():
                        if propNm == 'PIN_TYPE':
                            pin[propNm] = self.fixPinType[propVl]
                        elif propNm == 'PIN_NAME':
                            pin[propNm] = propVl
                    Devs[primName]['PINS'][pinDct['PIN_NUMBER']] = pin
        #
        return([Devs, Refs])
    
    def getOrcadDevs(self):
        chips = self.Orcad.chips['DATA'].copy()  # We're deleting stuff, so make a copy
        xprts = self.Orcad.xprts['DATA']
        devs = SortedDict()
        refs = SortedDict()
        for primName,descDct in chips.items():  # Part names
            if not primName in devs:
                devs[primName] = SortedDict({  
                    'PINS': SortedDict(),  
                    'PART': SortedDict()  
                })
            else:
                print('ERROR: getOrcadDevs: should never happen'); exit(1)
            #
            devs[primName]['PART'] = descDct['BODY'].copy()
            if primName.find('_') != -1:
                devs[primName]['PART']['PART_TYPE'] = primName[:primName.find('_')]
            else:
                x = devs[primName]['PART']['PART_NAME']
                devs[primName]['PART']['PART_TYPE'] = x[:x.find('_')]
            #
            try:
                devs[primName]['PART']['PART_TYPE3'] = devs[primName]['PART']['JEDEC_TYPE']
            except KeyError:
                devs[primName]['PART']['PART_TYPE3'] = ''
            devs[primName]['PART']['PART_TYPE2'] =  \
                devs[primName]['PART']['PART_TYPE']+'_'+devs[primName]['PART']['PART_TYPE3']
            #
            devs[primName]['PINS'] = SortedDict()
            for pinName,pinDct in descDct['PIN'].items():
                pin = SortedDict()
                pinNums = pinDct['PIN_NUMBER']
                if isinstance(pinNums, (str,)):
                    pinNums = [pinNums]
                pin['PIN_NAME'] = pinName
                for pinNum in pinNums:
                    if 'PINUSE' in pinDct:
                        if pinDct['PINUSE'] in ['POWER','GROUND']:
                            pin['PIN_TYPE'] = 'POWER'
                        else:
                            if 'BIDIRECTIONAL' in pinDct:
                                pin['PIN_TYPE'] = 'BIDI'
                            elif 'OUTPUT_TYPE' in pinDct:
                                pin['PIN_TYPE'] = 'OUTPUT'
                            elif 'OUTPUT_LOAD' in pinDct:
                                pin['PIN_TYPE'] = 'OUTPUT'
                            else:
                                pin['PIN_TYPE'] = 'INPUT'
                    else:
                        if 'BIDIRECTIONAL' in pinDct:
                            pin['PIN_TYPE'] = 'BIDI'
                        elif 'OUTPUT_TYPE' in pinDct:
                            pin['PIN_TYPE'] = 'OUTPUT'
                        elif 'OUTPUT_LOAD' in pinDct:
                            pin['PIN_TYPE'] = 'OUTPUT'
                        else:
                            pin['PIN_TYPE'] = 'INPUT'
                    devs[primName]['PINS'][pinNum] = pin  # dict of pin data
        #
        for ref,descDct in xprts.items():  # refdes to primName
            if len(descDct):
                refs[ref] = descDct['PART_NAME']
        #
        return([devs, refs])
    
    def getAltiumDevs(self):
        return([None, None])
    
    def checkFiletype(self):
        if not defined(self._filetype):
            print('ERROR: no file type defined'); exit(1)
        elif not self._filetype in self.ftypes:
            print('ERROR: "%s" filetype not recognized'%self._filetype); exit(1)
        return(self._filetype)

##############
    '''
    Getting suspicious about the database integrity? Run this script
    '''
    def checkDbIntegrity(self,rpt=True):
        self.checkNets(rpt)
        self.checkFlatNets(rpt)
        #
        if len(self.Actives):
            self.checkActives(rpt)
        if len(self.NoConnectList):
            self.checkNoConnectList(rpt)
        if len(self.IgnoreList):
            self.checkIgnoreList(rpt)
        if len(self.ConnectorList):
            self.checkConnectorList(rpt)
        if len(self.PwrGndAdded):
            self.checkPwrGndAdded(rpt)

    def checkNets(self,rpt=False):
        print('database \'byNet\'') if rpt else None
        byNet = self.byNet
        netsPerPin = {}
        for net,refDct in byNet.items():
            for ref,pinsLst in refDct.items():
                for pinDct in pinsLst:
                    pin = '%s.%s'%(ref,pinDct['PIN_NUMBER'])
                    if not pin in netsPerPin:
                        netsPerPin[pin] = 1
                    else:
                        netsPerPin[pin] += 1
        #
        for net,pinCnt in netsPerPin.items():
            if pinCnt > 1:
                if rpt:
                    print('>>>checkDbIntegrity: byNet: pin count for %s = %d'%(net,pinCnt))
                else:
                    return(False)
        return(True)
        
    def checkFlatNets(self,rpt=False):
        print('database \'flatNet\'') if rpt else None
        flatNet = self.flatNet
        netsPerPin = {}
        for net,pinsLst in flatNet.items():
            for pin in pinsLst:
                if not pin in netsPerPin:
                    netsPerPin[pin] = 1
                else:
                    netsPerPin[pin] += 1
        #
        for net,pinCnt in netsPerPin.items():
            if pinCnt > 1:
                if rpt:
                    print('>>>checkDbIntegrity: flatNet: pin count for %s = %d'%(net,pinCnt))
                else:
                    return(False)
        return(True)
        
    def checkActives(self,rpt=False):
        print('design data \'Actives\'') if rpt else None
        part_type2 = []
        for part,dev in self.Devs.items():
            part_type2.append(dev['PART']['PART_TYPE2'])
        ###
        
        unknown = []
        for dev in self.Actives:
            if not dev in part_type2:
                unknown.append(dev)
        if len(unknown) > 0:
            if rpt:
                print('>>>checkDbIntegrity: %s'%(', '.join(unknown)))
            else:
                return(False)
        return(True)

    def checkNoConnectList(self,rpt=False):
        print('design data \'NoConnectList\'') if rpt else None
        unknown = []
        for net in self.NoConnectList:
            if not net in self.Nets:
                unknown.append(net)
        if len(unknown) > 0:
            if rpt:
                print('>>>checkDbIntegrity: %s'%(', '.join(unknown)))
            else:
                return(False)
        return(True)
        
    def checkIgnoreList(self,rpt=False):
        print('design data \'IgnoreList\'') if rpt else None
        unknown = []
        for net in self.IgnoreList:
            if not net in self.Nets:
                unknown.append(net)
        if len(unknown) > 0:
            if rpt:
                print('>>>checkDbIntegrity: %s'%(', '.join(unknown)))
            else:
                return(False)
        return(True)
        
    def checkConnectorList(self,rpt=False):
        print('design data \'ConnectorList\'') if rpt else None
        unknown = []
        for ref in self.ConnectorList:
            if not ref in self.Refs:
                unknown.append(ref)
        if len(unknown) > 0:
            if rpt:
                print('>>>checkDbIntegrity: %s'%(', '.join(unknown)))
            else:
                return(False)
        return(True)
        
    def checkPwrGndAdded(self,rpt=False):
        print('design data \'PwrGndAdded\'') if rpt else None
        unknown = []
        for net in self.PwrGndAdded:
            if not net in self.Refs:
                unknown.append(net)
        if len(unknown) > 0:
            if rpt:
                print('>>>checkDbIntegrity: %s'%(', '.join(unknown)))
            else:
                return(False)
        return(True)

##############
    '''
    See "byNet" for data structure returned by readNetlist
    '''
    def readNetlist(self,fname=None,ftype=None):
        if defined(fname):
            self._filename = fname
        elif not defined(self._filename):
            print('ERROR: filename not defined'); exit(1)
        #
        if defined(ftype):
            self._filetype = ftype
        elif not defined(self._filetype):
            self._filetype = getFileType(self._filename)
            #print('getFileType',self._filetype)
        ##
        if self._filetype == 'Allegro':
            self.Allegro = readAllegroNets(self._filename)
            self._byNet = self.Allegro.nets['NETS']
            #
            self._Devs, self._Refs = self.getAllegroDevs()
        elif self._filetype == 'OrCad':
            self.Orcad = readOrcadNets(self._filename)
            self._byNet = self.Orcad.xnets['NETS']
            #
            self._Devs, self._Refs = self.getOrcadDevs()
            addOrcadProps(self)
        elif self._filetype == 'Altium':
            self.Altium = readAltiumNets(self._filename)
            #print('self.Altium.refs=%s'%len(self.Altium.refs))
            self._byNet = self.Altium.nets['NETS']
            self._byRef = self.Altium.refs
            #
            #self._byDev = self.getAltiumDevs()
        else:
            print('ERROR: "%s" filetype not recognized'%self._filetype); exit(1)
        return(self._byNet)
    
    '''
    Data structure of net2ref output, displayed in JSON format:
    {
      "D1": {  # REFDES
        "A": {  # PIN_NUMBER
          "NET": "P3V3_PCH",
          "PIN_NAME": "A"
        },
        "C": {
          "NET": "P3V3_RTC",
          "PIN_NAME": "C"
        }
      },
      ...
    }
    '''
    def net2ref(self):
        # Take a Netlist based data structure, reorganize to a RefDes data structure
        byNet = self.byNet.copy()
        byRef = SortedDict()
        for net,Ndat in byNet.items():  # NET_NAME
            for refdes,Rdat in Ndat.items():  # REFDES
                if not refdes in byRef:
                    byRef[refdes] = SortedDict()
                for pin in Rdat:  # list of pins
                    if pin['PIN_NUMBER'] in byRef[refdes]:
                        print('Error: net2ref check#1'); exit(1)
                    byRef[refdes][pin['PIN_NUMBER']] = SortedDict({
                        'NET': net,
                        'PIN_NAME': pin['PIN_NAME']
                    })
        self._byRef = byRef
        return(self._byRef)

    def ref2net(self):
        return(None)
    
    '''
    Add pins to a refdes
    pinList looks like a list of strings, "refdes"."pin"
    Example: ['U1.5','U1.6','U1.7']
    '''
    def addPins(self,pinList):
        byRef = self.byRef.copy()
        byNet = self.byNet.copy()
        for pinref in pinList:
            ref = pinref.split('.')[0]
            pin = pinref.split('.')[1]
            #print('Ref %s, Pin %s'%(ref,pin)); exit(1)
            byRef[ref][pin] = SortedDict({'NET': None})
    
    '''
    Print a flat netlist to output
    '''
    def printNetlistByNet(self,useX=False):
        print('Netlist filename: %s\n'%self.filename)
        print('NetName,Pin List,')
        netlist = self.makeFlatByNet(useX=useX)
        for net,pins in netlist.items():
            print('%s,"%s",'%(net,','.join(pins)))
        return()
    
    def reportPinProperties(self,PinsList):
        if not defined(PinsList):
            print('reportPinProperties: ERROR: PinsList not defined'); exit(1)
        #
        byNet = self.byNet.copy()
        byRef = self._byRef
        # Dump the pin properties list of parts in PartList
        report = []
        print('refdes.pin,pin name,pin type,')
        for i,net in byNet.items():
            for ref,hdl in net.items():
                if len(byRef[ref]) in PinsList:
                    for pin in hdl:
                        if 'PIN_TYPE' in pin:
                            report.append( 
            '%s.%s,%s,%s'%(ref,pin['PIN_NUMBER'],pin['PIN_NAME'],pin['PIN_TYPE']) 
            )
        report.sort()
        return(report)
    
    def reportShorted2pins(self,ext='TXT'):
        refs = self.byRef
        #
        ## look for shorted two-pin passives
        for ref,pinsDct in refs.items():
            if self.isPassive(ref):
                last = None
                for pin,propDct in pinsDct.items():
                    if propDct['NET'] == last:
                        print('Ref %s shorted on net %s'%(ref,propDct['NET']))
                    else:
                        last = propDct['NET']
        #
        ## look for two-pin passives in parralel, and not on VDD/GND (ignore bypass caps)
        print()
        nets = self.byNet
        for net,refsDct in nets.items():
            if not self.isPowerNet(net):
                otherNets = {}; otherNet = None; otherRef = None
                for ref,pinsLst in refsDct.items():
                    if self.isPassive(ref) and len(pinsLst)==1:
                        pinNum = pinsLst[0]['PIN_NUMBER']
                        for pin,propDct in refs[ref].items():
                            if pin != pinNum:
                                otherNet = propDct['NET']
                        otherNet = self.getOtherPinNet(ref,pinNum)
                        if otherNet in otherNets:
                            name     = self.getNameByRef(ref)
                            val      = self.getValByRef(ref)
                            otherRef = otherNets[otherNet]
                            otherNam = self.getNameByRef(otherRef)
                            otherVal = self.getValByRef(otherRef)
                            if name == otherNam:
                                if ext == 'TXT' or ext == None:
                                    print('Refs %s,%s & %s,%s are in parallel on nets %s & %s'%(ref,val,otherRef,otherVal,net,otherNet))
                                elif ext == 'CSV':
                                    #print('Ref1,Val1,Ref2,Val2,Net1,Net2\n',end='')
                                    print('%s,%s,%s,%s,%s,%s'%(ref,val,otherRef,otherVal,net,otherNet))
                                else:
                                    print('ERROR: should never get here'); exit(1)
                        else:
                            otherNets[otherNet] = ref
    
#######################################################################
# An object to analyze nets, individually
class nodeStruct(Netlist):
    type = 'NodeStruct'  # type = Net
    def __init__(self,Brd,NetName=None):
        self._Brd         = None  # board handle of type 'Netlist'
        self._NetName     = None  # string, name of net of interest
        self._Net         = None  # dict struct describing the net connections
        self._Active      = []  # Active comps
        self._PassiveThru = []  # Passive thru-signal comps
        self._PullUp      = []  # Passive pull-ups
        self._PullDown    = []  # Passive pull-downs
        self._Connector   = []  # connectors
        self._Empty       = []  # No-stuff comps
        self._Other       = []  # catch-all for anything else
        #
        if defined(Brd):
            self.Brd = Brd
        if defined(NetName):
            self.NetName = NetName

    @property
    def Brd(self):
        return(self._Brd)
    @Brd.setter
    def Brd(self,Brd):
        self._Brd = Brd
    
    @property
    def Net(self):
        return(self._NetName)
    
    @property
    def NetName(self):
        return(self._NetName)
    @Net.setter
    def NetName(self,NetName):
        self.__init__(self._Brd)  # Reinitialize an old object
		#
        self._NetName = NetName
        self.nodeAnlyz()
    
    @property
    def Active(self):
        return(self._Active)
    @Active.setter
    def Active(self,Active):
        self._Active = Active
    
    @property
    def PassiveThru(self):
        return(self._PassiveThru)
    @PassiveThru.setter
    def PassiveThru(self,PassiveThru):
        self._PassiveThru = PassiveThru
    
    @property
    def PullUp(self):
        return(self._PullUp)
    @PullUp.setter
    def PullUp(self,PullUp):
        self._PullUp = PullUp
    
    @property
    def PullDown(self):
        return(self._PullDown)
    @PullDown.setter
    def PullDown(self,PullDown):
        self._PullDown = PullDown
    
    @property
    def Connector(self):
        return(self._Connector)
    @Connector.setter
    def Connector(self,Connector):
        self._Connector = Connector
    
    @property
    def Empty(self):
        return(self._Empty)
    @Empty.setter
    def Empty(self,Empty):
        self._Empty = Empty
    
    @property
    def Other(self):
        return(self._Other)
    @Other.setter
    def Other(self,Other):
        self._Other = Other
    
    def nodeAnlyz(self):
        Brd = self.Brd
        Net = Brd.byXnet[self._NetName]
        self._Net = Net
        Refs = Brd.Refs
        Devs = Brd.Devs
        #
        for ref,pinsLst in Net.items():
            primName = Refs[ref]
            partPrps = Devs[primName]['PART']
            partType2 = partPrps['PART_TYPE2']
            partType3 = partPrps['PART_TYPE3']
            #
            if Brd.isPassive(ref):
                if Brd.isPullUpDown(ref):
                    if Brd.isPullDown(ref):
                        self.PullDown.append(ref)
                    else:
                        self.PullUp.append(ref)
                else:
                    self.PassiveThru.append(ref)
            else:
                if ref[:1] == 'J':
                    self.Connector.append(ref)
                elif ref in Brd.ConnectorList:
                    self.Connector.append(ref)
                elif partType2 in Brd.Actives:
                    self.Active.append(ref)
                else:
                    self.Other.append(ref)
                if partType3 == 'EMPTY':
                    self.Empty.append(ref)
    
    def nodeCompare(self,Anet,Bnet):
        attrOrder = ['Active','PassiveThru','PullUp','PullDown','Connector','Other']
        for attr in attrOrder:
            Aval = Anet.__getattribute__('_'+attr)
            Bval = Bnet.__getattribute__('_'+attr)
            if len(Aval) != len(Bval):
                return(False)
        return(True)

    def nodeCompare2(self,Anet,Bnet):
        attrOrder = ['Active','PassiveThru','PullUp','PullDown','Connector','Other']
        for attr in attrOrder:
            Aval = Anet.__getattribute__('_'+attr)
            Bval = Bnet.__getattribute__('_'+attr)
            if len(Aval) != len(Bval):
                return(False)
            
        return(True)

    def nodeDiff(self,Anet,Bnet):
        attrOrder = ['Active','PassiveThru','PullUp','PullDown','Connector','Other','Empty']
        diff = OrderedDict()
        for attr in attrOrder:
            Aval = Anet.__getattribute__('_'+attr)
            Bval = Bnet.__getattribute__('_'+attr)
            diff[attr] = SortedDict()
            if len(Aval) != len(Bval):
                diff[attr]['A'] = Aval
                diff[attr]['B'] = Bval
                #diff[attr]['A'] = '"%s"'%','.join(Aval)
                #diff[attr]['B'] = '"%s"'%','.join(Bval)
            else:
                diff[attr]['A'] = Aval
                diff[attr]['B'] = Bval
                #diff[attr]['A'] = '"%s"'%','.join(Aval)
                #diff[attr]['B'] = '"%s"'%','.join(Bval)
                # diff[attr]['A'] = '" ="'
                # diff[attr]['B'] = '" ="'
        return(diff)
    
    def nodeReport(self,header=False):
        attrOrder = ['Active','PassiveThru','PullUp','PullDown','Connector','Other','Empty']
        #
        if header:
            return(attrOrder)
        #
        report = []
        for attr in attrOrder:
            #print('_%s = %s'%(attr,str(','.join(self.__getattribute__('_'+attr)))))
            val = '"%s"'%','.join(self.__getattribute__('_'+attr))
            report.append(val)
        return(report)
        
    def dumpAttributes(self):
        struct = OrderedDict()
        struct['Brd'] = self._Brd.nick
        struct['NetName'] = self._NetName
        struct['Net'] = self._Net
        struct['Active'] = ','.join(self._Active)
        struct['PassiveThru'] = ','.join(self._PassiveThru)
        struct['PullUp'] = ','.join(self._PullUp)
        struct['PullDown'] = ','.join(self._PullDown)
        struct['Connector'] = ','.join(self._Connector)
        struct['Empty'] = ','.join(self._Empty)
        struct['Other'] = ','.join(self._Other)
        return(struct)
    
#######################################################################
# An object to hold two Netlist objects, with intent to compare them
class twoLists(Netlist):
    def __init__(self, A, B):
        self.A = A
        self.B = B
        self.A._brdID = 'A'  # nickname for board A
        self.B._brdID = 'B'  # nickname for board B
        #
        self._allPins = None
        self._commonPins = None
        self._refByPinCount = None
        self._PinsList = None
        self._PinProperties = None
        self._numPnsList = None
        #
        self._Netlist = {'A': self.A, 'B': self.B}
        self._netXref = SortedDict({  
            'A':SortedDict(),  
            'B':SortedDict()  
        })
        self._FoundNets = SortedDict({  
            'A':SortedDict(),  
            'B':SortedDict()  
        })
        #
        self._NetsNotes = []
        self._PwrNotes  = []
        self._SaveNotes = []
        #
        #self._refdesPairs = {'NAME': {'A': refdes, 'B': refdes} }
        self._refdesPairs = None
        self._refdesLookup = None
        # debug attributes
        #self.countPinsListSetter = 0

    ################################################
    ## Properties
    
    @property
    def Netlist(self,brd=None):
        if defined(brd):
            return(self._Netlist[brd])
        else:
            return(self._Netlist)

    @property
    def NetXref(self):
        return(self._netXref)
    
    @property
    def PinsList(self):
        return(self._PinsList)
    @PinsList.setter
    def PinsList(self,PinsList):
        self._PinsList = PinsList
        
    @property
    def numPnsList(self):
        return(self._numPnsList)
    @numPnsList.setter
    def numPnsList(self,num):
        self._numPnsList = num
    
    @property
    def refdesPairs(self):
        if not defined(self._refdesPairs):
            self._refdesPairs = SortedDict()
        return(self._refdesPairs)
    @refdesPairs.setter
    def refdesPairs(self,pairs):
        self._refdesPairs, self._refdesLookup = self.setRefdesPairs(pairs)
        return(self._refdesPairs)
    
    @property
    def refdesLookup(self):
        if not defined(self._refdesLookup):
            self._refdesLookup = SortedDict()
        return(self._refdesLookup)

    @property
    def allPins(self):
        if not defined(self._allPins):
            self._allPins = self.getAllPins()
        return(self._allPins)
    
    @property
    def commonPins(self):
        if not defined(self._commonPins):
            self._commonPins = self.getCommonPins()
        return(self._commonPins)
    
   ################################################
    ##
    
    def setRefdesPairs(self,pairs):
        refdesPairs = SortedDict()
        for name,brds in pairs.items():
            refdesPairs[name] = OrderedDict({'NAME':name, 'A':brds['A'], 'B':brds['B']})
        #
        refdesLookup = SortedDict()
        for name,pair in refdesPairs.items():
            refdesLookup['N_'+name]      = refdesPairs[name]
            refdesLookup['A_'+pair['A']] = refdesPairs[name]
            refdesLookup['B_'+pair['B']] = refdesPairs[name]
        #print('refdesLookup:',json.dumps(list(refdesLookup.keys()), indent=2)); exit(1)
        return([refdesPairs, refdesLookup])
    
    def getNetXref(self,Brd):  # consider using self.NetXref['A'][Anet]; returns Bnet
        return(self._netXref[Brd])
        #
    def setNetXref(self,Anet,Bnet):
        self._netXref['A'][Anet] = Bnet;
        self._netXref['B'][Bnet] = Anet;
    
    def getAllPins(self):
        '''
        Make a list of pin counts. Just a simple list
        '''
        nums_a = list(self.A.pinCount.keys())
        nums_b = list(self.B.pinCount.keys())
        '''
        Combine A and B's pincount list so we can display them side by side, below
        This is just a list of numbers. We'll use it to compare A and B
        '''
        allPins = SortedDict()  # using a Dict guarrantees uniqueness
        for n in nums_a:
            allPins[n] = n
        for n in nums_b:
            allPins[n] = n
        allPins = list(allPins.keys())
        allPins.reverse()  # Biggest to smallest
        return(allPins)

    def getCommonPins(self):
        '''
        Make a list of pin counts. Just a simple list
        '''
        nums_a = list(self.A.pinCount.keys())
        nums_b = list(self.B.pinCount.keys())
        '''
        Combine A and B's pincount list so we can display them side by side, below
        This is just a list of numbers. We'll use it to compare A and B
        '''
        commonPins = []
        for n in nums_a:
            if n in nums_b:
                commonPins.append(n)
        commonPins.sort()
        commonPins.reverse()  # Biggest to smallest
        return(commonPins)

    def getObj(self,Name):
        #print('Name: "%s"'%str(Name)); 
        if not Name in self.Netlist:
            print('ERROR: getObj: cant find object "%s"'%Name);exit(1)
        return(self.Netlist[Name])

    '''
    RefDes-by-pincount data structure:
    RefDes -> {
        <Pincount X>: {  # List of refdes in A & B with pincount = X
          'A': 
            [ # Board 'A' list of refdes with pincount X
              refdes1, refdes2, ...
            ],
          'B': 
            [ # Board 'B' list of refdes with pincount X
              refdes1, refdes2, ...
            ]
          },
        <Pincount Y>: {  # List of refdes in A & B with pincount = Y
          'A': [ # Board 'A' list of refdes with pincount Y
                 refdes1, refdes2, ...
               ],
          'B': [ # Board 'B' list of refdes with pincount Y
                 refdes1, refdes2, ...
                ]
        },
        ...
      }
    '''
    def refdesByPincount(self,PinsList=None):
        if not defined(self._PinsList) and not defined(PinsList):
            print('refdesByPincount: ERROR: PinsList not defined'); exit(1)
        elif defined(PinsList):
            self._PinsList = PinsList
            self._refByPinCount = None
        #
        if not defined(self._refByPinCount):
            if not defined(self._numPnsList) or \
            (self._numPnsList > len(self._PinsList)):
                self._numPnsList = len(self._PinsList)
            PinsList = self._PinsList[:self._numPnsList]
            A_pinCount = self.A.pinCount; B_pinCount = self.B.pinCount
            RefDes = OrderedDict()
            for n in PinsList:
                if not n in RefDes:
                    RefDes[n] = SortedDict()
                RefDes[n]['A'] = A_pinCount[n]
                RefDes[n]['B'] = B_pinCount[n]
                #print('refdes:',RefDes[n]['A'][0],RefDes[n]['B'][0])
            self._refByPinCount = RefDes
        return(self._refByPinCount)
    
    def diffNetsByName(self,AnetName,BnetName):
        Anet = self.A.flatNet[AnetName]
        Bnet = self.B.flatNet[BnetName]
        netDiffs = SortedDict({'A':[], 'B':[]})
        for Apin in Anet:
            if Apin not in Bnet:
                #netDiffs['A'].append('A.%s'%Apin)
                netDiffs['A'].append('%s'%Apin)
        for Bpin in Bnet:
            if Bpin not in Anet:
                #netDiffs['B'].append('B.%s'%Bpin)
                netDiffs['B'].append('%s'%Bpin)
        #print('\nnetDiffs:\n%s'%json.dumps(netDiffs, indent=2)); exit(1)
        return(netDiffs)
        
    def diffXnetsByName(self,AnetName,BnetName):
        Anet = self.A.flatXnet[AnetName]
        Bnet = self.B.flatXnet[BnetName]
        netDiffs = SortedDict({'A':[], 'B':[]})
        for Apin in Anet:
            if Apin not in Bnet:
                #netDiffs['A'].append('A.%s'%Apin)
                netDiffs['A'].append('%s'%Apin)
        for Bpin in Bnet:
            if Bpin not in Anet:
                #netDiffs['B'].append('B.%s'%Bpin)
                netDiffs['B'].append('%s'%Bpin)
        #print('\nnetDiffs:\n%s'%json.dumps(netDiffs, indent=2)); exit(1)
        return(netDiffs)
    
    #####################
    
    def found(self,brd,pin,net):
        # Keep a memory of netlists we have seen
        found = net in self._FoundNets[brd]
        self._FoundNets[brd][net] = 1
        #print('board=%s pin=%s net=%s found=%s'%(brd,pin,net,found))
        return(found)  # Have we seen this net before? True/False

    '''
    Note: A & B can be either 'A' or 'B'
    '''
    def getPins(self,A,Aref,B,Bref):
        #print('in getPins')
        Aobj = self.getObj(A); Bobj = self.getObj(B)
        #print('A.nick="%s" B.nick="%s"'%(Aobj.nick,Bobj.nick))
        # This routine guarrantees that the two pin lists are aligned one-to-one
        Apins = list(Aobj.byRef[Aref].keys())
        Bpins = list(Bobj.byRef[Bref].keys())
        foundPins = SortedDict({'A': [], 'B': []})
        lostPins  = SortedDict({'A': [], 'B': []})
        #
        for Apin in Apins:
            if Apin in Bpins:
                Bpin = Apin
                Bpins.remove(Bpin)
                foundPins['A'].append(Apin)
                foundPins['B'].append(Bpin)
            else:
                lostPins['A'].append(Apin)
        lostPins['B'].extend(Bpins)
        #
        foundPins['A'].sort(); foundPins['B'].sort()
        lostPins['A'].sort(); lostPins['B'].sort()
        #
        if len(lostPins['A']):
            self._SaveNotes.append('Lost pins, %s.%s.%s'%(Aobj.nick,Aref,str(lostPins['A'])))
        if len(lostPins['B']):
            self._SaveNotes.append('Lost pins, %s.%s.%s'%(Bobj.nick,Bref,str(lostPins['B'])))
        return([foundPins,lostPins])

#####################
#####################
    '''
    Note: A & B can be either 'A' or 'B'
    '''
    def EquateNetNames(self,A,Aref,B,Bref):
        # The heart of this method of netlist comparing. One RefDes pair at a time
        # This assumes someone knows what refdes's on brd 'A' correspond to brd 'B'
        #
        # Output is through print()'s to stdout
        Aobj = self.getObj(A); Bobj = self.getObj(B)
        IgnoreList = Aobj.IgnoreList + Bobj.IgnoreList
        #
        A_byRef = Aobj.byRef; A_flatXnet = Aobj.flatNet
        B_byRef = Bobj.byRef; B_flatXnet = Bobj.flatNet
        #
        foundPins, x = self.getPins(A,Aref,B,Bref)  # returns: [foundPins,lostPins] 
        #print(json.dumps(lostPins, indent=2)); exit(1)
        #
        Apins = foundPins['A'];  # use the foundPins list; ignore lostPins
        #print('%s: %s'%(Aref,','.join(Apins))); exit(1)
        Bpins = foundPins['B'];  # use the foundPins list; ignore lostPins 
        #print('%s: %s'%(Bref,','.join(Bpins))); exit(1)
        #
        #print('#Apins=%d'%len(Apins),'#Bpins=%d'%len(Bpins)); exit(1)
        print('Examining refdes %s.%s & %s.%s - %d & %d pins each'% 
            (A,Aref,B,Bref,len(Apins),len(Bpins)))
        for Apin,Bpin in zip(Apins,Bpins):
            Anet = A_byRef[Aref][Apin]['NET']
            Bnet = B_byRef[Bref][Bpin]['NET']
            #
            self.A.isXnet(Anet)
            self.B.isXnet(Bnet)
            #
            Afound=self.found('A',Apin,Anet); Bfound=self.found('B',Bpin,Bnet)
            if Afound != Bfound: 
                if not Anet in IgnoreList and not Bnet in IgnoreList: 
                    netDiffs = self.diffNetsByName(Anet,Bnet)
                    note = '%s.%s.%s,%s,%s.%s.%s,%s,%d,%d,'% \
                        (A,Aref,Apin,Anet, \
                         B,Bref,Bpin,Bnet, \
                         #str(A_flatXnet[Anet]),str(B_flatXnet[Bnet])) \
                         len(self.A.flatNet[Anet]), \
                         len(self.B.flatNet[Bnet]) \
                        )
                    if self.A.isPowerNet(Anet) or self.B.isPowerNet(Bnet):
                        note += 'Power net?'
                    if self.A.isNoConnectNet(Anet) or self.B.isNoConnectNet(Bnet):
                        note += 'No Connect net?'
                    note += ','
                    #note += '%s,'%(self.A.getPinType(Aref,Apin))
                    self._SaveNotes.append(note)
            if not Afound and not Bfound:
                self.setNetXref(Anet,Bnet)
                note =  \
                    '%s.%s.%s,%s,'%(A,Aref,Apin,Anet) +  \
                    '%s.%s.%s,%s,'%(B,Bref,Bpin,Bnet) +  \
                    '%d,%d,'%(  \
                        len(self.A.flatNet[Anet]),  \
                        len(self.B.flatNet[Bnet])  \
                    )
                if self.A.isPowerNet(Anet) or self.B.isPowerNet(Bnet):
                    self._PwrNotes.append(note)
                else:
                    self._NetsNotes.append(note)
        print()
        
    def checkNetNames(self):
        #print('in checkNetNames')
        RefDes = self.refdesByPincount()
        for numPins in RefDes.keys():
            Arefs = RefDes[numPins]['A']
            Brefs = RefDes[numPins]['B']
            #
            for Aref,Bref in zip(Arefs,Brefs):
                self.EquateNetNames('A',Aref,'B',Bref)
        self.reportNetsNotes()
        self.reportPwrNotes()
    
    '''
    Note: A & B can be either 'A' or 'B'
    '''
    def checkPin2PinAtRefdes(self,A,Aref,B,Bref):
        #print('in checkPin2PinAtRefdes')
        self.EquateNetNames(A,Aref,B,Bref)
        self.reportNetsNotes()
        self.reportPwrNotes()
    
#####################
#####################

    '''
    A quick routine to show how nets, Xnets and their cross-reference is used
    '''
    def demoXnet(self,Brd):  # "Brd" is either 'A' or 'B'
        pnote = []
        A = self.getObj(Brd)
        for ref,pinsDct in A.byRef.items():
            pnote.append('Refdes %s:\n'%ref)
            for pin,propsDct in pinsDct.items():
                net = propsDct['NET']
                pnote.append(' Net %s is'%net)
                if A.isXnet(net):
                    pnote.append(' an Xnet,')
                    pnote.append(' %s\n'%A.XnetXref[net])
                else:
                    pnote.append(' not an Xnet\n')
        print(''.join(pnote))
    
    '''
    Note: A & B can be either 'A' or 'B'
    '''
    def EquatePin2PinConnections(self,A,Aref,B,Bref):
        Aobj = self.getObj(A);   Bobj = self.getObj(B)
        A_h = nodeStruct(Aobj); B_h = nodeStruct(Bobj)
        #
        A_byRef = Aobj.byRef; A_flatXnet = Aobj.flatXnet
        B_byRef = Bobj.byRef; B_flatXnet = Bobj.flatXnet
        ##
        ###############
        ##
        foundPins, x = self.getPins(A,Aref,B,Bref)  # returns: [foundPins,lostPins] 
        Apins = foundPins['A'];  # use the foundPins list; ignore lostPins
        Bpins = foundPins['B'];  # use the foundPins list; ignore lostPins
        print('Examining refdes %s.%s & %s.%s - %d & %d pins each'% 
            (A,Aref,B,Bref,len(Apins),len(Bpins)))
        #
        lclXnets = []
        #
        print('Xnet difference report for %s.%s and %s.%s\n'%(A,Aref,B,Bref))
        header = []
        header.append('%s Xnet name,%s Xnet name,'%(A,B))
        for attrName in A_h.nodeReport(header=True):
            if attrName == 'Active':
                header.append('%s Dest dev,'%A)
            header.append('%s %s,'%(A,attrName))
            if attrName == 'Active':
                header.append('%s Dest dev,'%B)
            header.append('%s %s,'%(B,attrName))
        header.append('" "')
        print(''.join(header))
        #
        for Apin,Bpin in zip(Apins,Bpins):
            ###########
            AnetName = Aobj.toXnet(A_byRef[Aref][Apin]['NET'])
            Anet = Aobj.byXnet[AnetName]
            A_h.NetName = AnetName
            Aactives = A_h.Active #[:5]
            #names = list(self.refdesLookup.keys())
            #print('refdesLookup:',json.dumps(names, indent=2)); exit(1)
            #
            #if Aref in Aactives:
            #    Aactives.remove(Aref)
            Aalias = []
            for actv in Aactives:
                if 'A_'+actv in self.refdesLookup:
                    Aalias.append(self.refdesLookup['A_'+actv]['NAME'])
            if len(Aalias):
                Aalias = '"%s",'%','.join(Aalias)
            else:
                Aalias = '"",'
            # try:
                # Aalias = self.refdesLookup['A_'+Aactives[0]]['NAME']
            # except (ValueError, KeyError, IndexError):
                # Aalias = ""
            ###########
            BnetName = Bobj.toXnet(B_byRef[Bref][Bpin]['NET'])
            Bnet = Bobj.byXnet[BnetName]
            B_h.NetName = BnetName
            Bactives = B_h.Active #[:5]
            #if Bref in Bactives:
            #    Bactives.remove(Bref)
            Balias = []
            for actv in Bactives:
                if 'B_'+actv in self.refdesLookup:
                    Balias.append(self.refdesLookup['B_'+actv]['NAME'])
            if len(Balias):
                Balias = '"%s",'%','.join(Balias)
            else:
                Balias = '"",'
            # try:
                # Balias = self.refdesLookup['B_'+Bactives[0]]['NAME']
            # except (ValueError, KeyError, IndexError):
                # Balias = ""
            ###########
            ##
            lclXnets.append(AnetName)
            #
            self.setNetXref(AnetName,BnetName)
            #
            if (Aobj.isIgnoreNet(AnetName) or Aobj.isNoConnectNet(AnetName)) and  \
               (Bobj.isIgnoreNet(BnetName) or Bobj.isNoConnectNet(BnetName)):
                None
            elif Aobj.isPowerNet(AnetName) or Bobj.isPowerNet(BnetName):
                if not (Aobj.isPowerNet(AnetName) and Bobj.isPowerNet(BnetName)):
                    print('WARNING: Two nets found where only one is attached to power - ',end='')
                    print('%s net %s and %s net %s'%(Aobj.nick,AnetName,Bobj.nick,BnetName))
            else:
                #print('Flat Xnet:',AnetName,BnetName,A_flatXnet[AnetName][:5],B_flatXnet[BnetName][:5])
                #print('%s,%s'%(A_h.nodeReport(),B_h.nodeReport()))
                if not A_h.nodeCompare(A_h,B_h):
                    #print('nodeReport:,,%s'%',,'.join(A_h.nodeReport()))  # this shows its all there!!??
                    print('%s,%s,'%(AnetName,BnetName), end='')
                    for attr,diffs in A_h.nodeDiff(A_h,B_h).items():
                        if attr in ['PassiveThru','PullUp','PullDown']:
                            refs = []
                            for ref in diffs['A']:
                                refs.append('%s=%s'%(ref,Aobj.getValByRef(ref)))
                            diffs['A'] = '"%s"' % ','.join(refs)
                            refs = []
                            for ref in diffs['B']:
                                refs.append('%s=%s'%(ref,Bobj.getValByRef(ref)))
                            diffs['B'] = '"%s"' % ','.join(refs)
                        else:
                            diffs['A'] = '"%s"' % ','.join(diffs['A'])
                            diffs['B'] = '"%s"' % ','.join(diffs['B'])
                        #
                        if not AnetName in Aobj.NoConnectList:
                            if attr == 'Active':
                                print(Aalias, end='')
                            print('%s,' % diffs['A'], end='')
                        else:
                            if attr == 'Active':
                                print('" "," ",', end='')
                            else:
                                print('" ",', end='')
                        #
                        if not BnetName in Bobj.NoConnectList:
                            if attr == 'Active':
                                print(Balias, end='')
                            print('%s,' % diffs['B'], end='')
                        else:
                            if attr == 'Active':
                                print('" "," ",', end='')
                            else:
                                print('" ",', end='')
                    #print('Xnets different: %s, %s'%(AnetName,BnetName))
                    print('" "')
            '''
            print('%s'%json.dumps(A_h.dumpAttributes(), indent=2))
                print('%s'%json.dumps(B_h.dumpAttributes(), indent=2));exit(1)
                # print('%s.%s,%s,%s,%s,,'%(Aref,Apin,Aalias,';'.join(Aactives),AnetName),end='')
                # print('%s.%s,%s,%s,%s, '%(Bref,Bpin,Balias,';'.join(Bactives),BnetName),end='')
                # print()
            '''
        
#####################
#####################
    '''
    Note: A & B can be either 'A' or 'B'
    '''
    def reportMissingPinsByRefdes(self,A,Aref,B,Bref):
        #print('in reportMissingPinsByRefdes')
        Aobj = self.getObj(A); Bobj = self.getObj(B)
        #print('Compare pins of %s.%s to %s.%s'%(Aobj.nick,Aref,Bobj.nick,Bref))
        x, lostPins = self.getPins(A,Aref,B,Bref);  # returns: [foundPins,lostPins]
        #print(json.dumps(lostPins, indent=2)); exit(1)
        
        Apins = lostPins['A']; Bpins = lostPins['B']
        print('Found these extra pins:')
        print('Extra pins on %s.%s: '%(Aobj.nick,Aref),end='');
        print('%s'%', '.join(Apins)) if len(Apins)>0 else print('None')
        print('Extra pins on %s.%s: '%(Bobj.nick,Bref),end='');
        print('%s'%', '.join(Bpins)) if len(Bpins)>0 else print('None')
        return()
        
    #####################
    
    def reportPinCounts(self,ext='TXT'):
        allPins = self.allPins
        if defined(self.numPnsList):
            if self.numPnsList < len(allPins):
                allPins = allPins[:self.numPnsList]
        if ext=='TXT':
            '''
            Create a table. We can see the differences between board A and B
            '''
            A_likeRefs = self.A.likeRefs
            B_likeRefs = self.B.likeRefs
            if defined(self.numPnsList):
                if self.numPnsList < len(allPins):
                    allPins = allPins[:self.numPnsList]
            for n in allPins:
                print('Pin count: %4d   '%n,end='')
                print('A: %4d   '%A_likeRefs[n],end='') \
                    if n in A_likeRefs else print('A:        ',end='')
                print('B: %4d'%B_likeRefs[n]) \
                    if n in B_likeRefs else print('B:')
        elif ext=='CSV':
            '''
            Create a CSV spreadsheet comparing components by pincount between board A and B
            This is a pretty useful output for the first-pass study of two boards
            '''
            A_pinCount = self.A.pinCount; B_pinCount = self.B.pinCount
            A_RefDes = self.A.RefDes; B_RefDes = self.B.RefDes
            print('Pin Count,',end='')
            print(self.A.filename+' Board RefDes,'+self.A.filename+' Part Name,',end='')
            print(self.B.filename+' Board RefDes,'+self.B.filename+' Part Name')
            #
            for n in allPins:
                print('%d,'%n,end='')  # print pin count
                #
                if n in A_pinCount:  # print board A refdes and part_name
                    print('"%s",'%','.join(A_pinCount[n]),end='') 
                    print('"%s",'%A_RefDes[A_pinCount[n][0]]['PART_NAME'],end='') 
                else:
                    print(',,',end='')
                #
                if n in B_pinCount:  # print board B refdes and part_name
                    print('"%s",'%','.join(B_pinCount[n]),end='') 
                    print('"%s",'%B_RefDes[B_pinCount[n][0]]['PART_NAME'],end='') 
                #
                print()
        else:
            print('reportPinCounts: Unrecognized extension type'); exit(1)
    
#######################
    def reportNetsNotes(self):
        if len(self._NetsNotes):
            print()  # CR
            print('Signal Net Notes:')
            print('A: refdes.pin,net,B: refdes.pin,net,',end='')
            print('# A net pins,# B net pins,Notes,')
            #print('# ReportNotes:',len(self._SaveNotes))
            print('\n'.join(self._NetsNotes))
            return(1)
        else:
            return(0)
    
    def reportPwrNotes(self):
        if len(self._PwrNotes):
            print()  # CR
            print('Power Net Notes:')
            print('A: refdes.pin,net,B: refdes.pin,net,',end='')
            print('# A net pins,# B net pins,Notes,')
            #print('# ReportNotes:',len(self._SaveNotes))
            print('\n'.join(self._PwrNotes))
            return(1)
        else:
            return(0)
    
    def reportNotes(self):
        if len(self._SaveNotes):
            print()  # CR
            print('RED FLAGS:')
            print('A: refdes.pin,net,B: refdes.pin,net,',end='')
            print('# A pins not in B,# B pins not in A,Notes,')
            #print('# ReportNotes:',len(self._SaveNotes))
            print('\n'.join(self._SaveNotes))
            return(1)
        else:
            return(0)
        
    def straightNetlistCompare(self):
        A_flatNet = self.A.flatNet.copy()
        B_flatNet = self.B.flatNet.copy()
        #
        A_NetNames = list(A_flatNet.keys())
        B_NetNames = list(B_flatNet.keys())
        #
        for net in A_NetNames:
            if net in B_NetNames:
                pinsA = ','.join(sorted(A_flatNet[net]))
                pinsB = ','.join(sorted(B_flatNet[net]))
                if pinsA == pinsB:
                    del A_flatNet[net]
                    del B_flatNet[net]
        #
        if len(A_flatNet) == 0 and len(B_flatNet) == 0:
            print('Netlist %s and %s are same'%(self.A.filename,self.B.filename))
        else:
            print('Change list:')
            A_NetNames = list(A_flatNet.keys())
            B_NetNames = list(B_flatNet.keys())
            #
            for net in A_NetNames:
                if net in B_NetNames:
                    print('%4d %4d %s'%(len(A_flatNet[net]),len(B_flatNet[net]),net))
                    del A_flatNet[net]
                    del B_flatNet[net]
            #
            print('\nNets from A, deleted:')
            for net in A_flatNet.keys():
                print('%s'%net)
            print('\nNets from B, added:')
            for net in B_flatNet.keys():
                print('%s'%net)
    
#######################################################################
