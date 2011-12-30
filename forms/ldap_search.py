#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygtk, gtk, gtk.glade, ldap
from utils import *

class ldap_search:
    def __init__(self, pnote_app=None):
        gladefile = "glade/ldap_search.glade"
        windowname = "ldap_search"
        wTree = self.wTree = gtk.glade.XML(gladefile)
        self.w = wTree.get_widget(windowname)
        self.ldap_srv, self.base_dn, self.ldap_filter, self.return_str, self.result_list = wTree.get_widget('ldap_srv'), wTree.get_widget('base_dn'), wTree.get_widget('ldap_filter'), wTree.get_widget('return_str'), wTree.get_widget('result_list')
        self.retval = ''
        self.ldap_srv.set_text(get_config_key('ldap', 'server', '') )
        self.base_dn.set_text(get_config_key('ldap', 'base_dn', '') )
        self.ldap_filter.set_text(get_config_key('ldap', 'filter', '(uid=*)') )
        self.result_list_model = gtk.ListStore(str,str,str) # cn, uid, email
        self.result_list.set_model(self.result_list_model)
        self.result_list.set_headers_visible(True)
        renderer = gtk.CellRendererText()
        col0 = gtk.TreeViewColumn('cn', renderer,text=0)
        col1 = gtk.TreeViewColumn("email", renderer,text=1)
        col2 = gtk.TreeViewColumn("uid", renderer,text=2)
        col0.set_resizable(True)
        col1.set_resizable(True)
        col2.set_resizable(True)
        col0.set_min_width(200)
        col1.set_min_width(200)
        col2.set_min_width(100)
        self.result_list.append_column(col0)
        self.result_list.append_column(col1)
        self.result_list.append_column(col2)
        #self.result_list.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        #result_list.set_search_column(0)
    
        evtmap = { "on_bt_clear_clicked": self.on_bt_clear_clicked, \
                   "on_bt_find": self.on_bt_find_clicked, \
                   'on_bt_close': lambda o, d=None: self.destroy(), \
                   'on_ldap_search_destroy': lambda o, d=None: self.destroy(), \
                   'on_result_list_row_activated': self.on_result_list_row_activated
                 }
        wTree.signal_autoconnect(evtmap)

    def on_bt_clear_clicked(self, evt, data=None):
        self.retval = ''
        self.return_str.set_text(self.retval)
        
    def on_bt_find_clicked(self, evt, data=None):
        if self.ldap_srv.get_text().find(':') != -1:  host, port = self.ldap_srv.get_text().split(':')
        else: host, port = self.ldap_srv.get_text(), 389
        try:
            ldapobj = ldap.open(host, port=port)
            result = ldapobj.search_s(self.base_dn.get_text(), ldap.SCOPE_SUBTREE, self.ldap_filter.get_text(), ['uid','mail', 'cn'] )
            self.result_list_model.clear()
            for tuple2 in result:
                _data = tuple2[1]# a dict of search key attr
                print _data
                cn,uid,email ='','',''
                if 'mail' in _data:
                    if 'cn' in _data: cn =_data['cn'][0]
                    if 'uid' in _data: uid = _data['uid'][0]
                    email =  _data['mail'][0]
                    print cn,uid,email
                    self.result_list_model.append((cn, email, uid))
        except Exception, e: message_box('ldap error', "%s" % e )
                                       
        
    def on_result_list_row_activated(self, obj, path, view_col, data=None):
        model = obj.get_model()
        cn, uid, email = model[path][0], model[path][2], model[path][1] # not use cn and uid for now
        if self.retval == '': self.retval = email
        else:
            if self.retval.find(email) == -1:
                self.retval += ',%s' % email
        self.return_str.set_text(self.retval)
        self.return_str.set_tooltip_text(self.retval)

    def destroy(self):
        self.retval = self.return_str.get_text()
        save_config_key('ldap', 'server', self.ldap_srv.get_text() )
        save_config_key('ldap', 'base_dn', self.base_dn.get_text() )
        save_config_key('ldap', 'filter', self.ldap_filter.get_text() )
        self.w.destroy()
        self.wTree = None
        return True

    def run(self): return self.w.run()
        
    def get_result(self): return self.retval
    