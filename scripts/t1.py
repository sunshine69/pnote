#!/usr/bin/python

""" sample script to run inside pnote app
this scripts in this folder can be called using Menu / Run Scripts. Actually that menu can be run any kind of scripts (untested) but if you make script like below, it will integrate with pnote app - well use pnote app module and do things. Shareing live data with pnote app can be through its database

"""
# Set up the sys.path so we can import pnote module at will
import os, sys
app_dir = os.path.dirname(sys.path[0])
for _i in [sys.path[0], app_dir, app_dir + '/forms']: sys.path.append(_i) 

from utils import *
import pygtk, gtk, gobject

class Test(object):
	def __init__(self): print "hello"

print __file__

if __name__ == '__main__': 
	t = Test()

