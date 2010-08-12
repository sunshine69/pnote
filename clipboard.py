#!/usr/bin/env python

import os
import pygtk
pygtk.require('2.0')
import gtk, gobject
from utils import get_config_key

class ClipboardInfo:
    pass

class PnClipboard:
    # singal handler called when clipboard returns target data
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

    # signal handler called when the clipboard returns text data
    def clipboard_text_received(self, clipboard, text, data):
        if not text or text == '':
            return
        cbi = ClipboardInfo()
        cbi.text = text
        cbi.label = text[0:50].split(os.linesep)[0]
        # prepend and remove duplicate
        history = [info for info in self.clipboard_history
                   if info and info.text<>text]
        self.clipboard_history = ([cbi] + history)[:self.history_count]
        self.clipboard.request_targets(self.clipboard_targets_received, cbi)
        return

    # get the clipboard text
    def fetch_clipboard_info(self):
        self.clipboard.request_text(self.clipboard_text_received)
        return True

    def set_clipboard(self, text):
        self.clipboard.set_text(text)
        return

    def __init__(self):
        self.clipboard_history = []
        self.history_count = int(get_config_key('global', 'clipboard_history_size', '15'))
        self.clipboard = gtk.clipboard_get(selection="PRIMARY")
        #self.clipboard = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)
        self.clipboard.request_text(self.clipboard_text_received)
        gobject.timeout_add(1500, self.fetch_clipboard_info)
        return