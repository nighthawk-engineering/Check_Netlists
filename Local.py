# -*- coding: utf-8 -*-
"""
Created on Fri Apr 26 2019 

@author: mlgkschm (Ken Schmahl)
"""

from copy import copy

##############################################################################
# useful functions
def defined(var):
    return(var != None)

##############################################################################
def atoi(text):
    return int(text) if text.isdigit() else text

##############################################################################
def mkType(t_name='C'):  # Make a type to be used as a dict
    return(type(t_name, (object,), {}))

##############################################################################
def readFile(fname):
    #print('Filename',fname)
    with open(fname, 'r') as f:
        s = f.read()
    return(s)

##############################################################################
# A generic object
# C = type('C', (object,), {})
class Parms(object):  # Called Parms, short for "Parameters"
    def copy(self):  # make it easy to make copies of this object
        return(copy(self))

##############################################################################
