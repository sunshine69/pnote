#!/usr/bin/env python

import os, sys
import pygtk
pygtk.require('2.0')
import gtk, gobject
from utils import get_config_key

class ClipboardInfo:
    pass

class PnClipboard:
    # singal handler called when clipboard returns target data. Not used for now
    def clipboard_targets_received(self, clipboard, targets, info):
        if targets:
            # have to remove dups since Netscape is broken
            targ = {}
            for t in targets:
                targ[str(t)] = 0
            targ = targ.keys()
            targ.sort()
            info.targets = '\n'.join(targ)
        else:
            info.targets = None
            print 'No targets for:', info.text

        return

    def add_info(self, text):
      cbi = ClipboardInfo()
      cbi.text = text
      # prepend and remove duplicate
      history = [info for info in self.clipboard_history if info and info.text<>text]
      self.clipboard_history = ([cbi] + history)[:self.history_count]
      #self.clipboard.request_targets(self.clipboard_targets_received, cbi)
      return cbi
      
    # signal handler called when the clipboard returns text data
    def clipboard_text_received(self, clipboard, text, data):
        if not text or text == '':
            #self.got_content = False
            return 
        cbi = self.add_info(text)
        #self.got_content = True
        return 

    # get the clipboard text
    def fetch_clipboard_info(self):
        self.clipboard.request_text(self.clipboard_text_received)
        if sys.platform != 'win32':
          self.clipboard1.request_text(self.clipboard_text_received)
        return True

    def set_clipboard(self, text):
        self.clipboard.set_text(text)
        if sys.platform != 'win32': self.clipboard1.set_text(text)
        return

    def __init__(self):
        self.clipboard_history = []
        #self.got_content = None
        self.history_count = int(get_config_key('global', 'clipboard_history_size', '15'))
        self.clipboard = gtk.clipboard_get(selection="PRIMARY")
        if sys.platform != 'win32': self.clipboard1 = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)
        self.clipboard.request_text(self.clipboard_text_received)
        self.clipboard1.request_text(self.clipboard_text_received)
        gobject.timeout_add(1500, self.fetch_clipboard_info)
        return