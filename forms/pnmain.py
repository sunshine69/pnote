#!/usr/bin/env python
# -*- coding: utf-8 -*-

# The main search window.
import os

try:
 import pygtk 
 pygtk.require('2.0')
except:
 pass
 
try:
 import gtk #, gobject
 import gtk.glade
except:
 pass

import sqlite3, types
from forms import pnote_new
from utils import *

class pnmain:
  
  def __init__(self, dbpath, pnote_app=None):
    self.app = pnote_app
    self.dbpath = dbpath
    self.dbcon = self.app.dbcon
    self.DEBUG = True
    self.kwcount = 0
    gladefile = "glade/pnote.glade"
    windowname = "pnote"
    self.wTree = gtk.glade.XML(gladefile)
    w = self.w = self.wTree.get_widget(windowname)
    self.keyword = self.wTree.get_widget('keyword')
    self.pn_completion = PnCompletion(get_config_key('data', 'keywords', ''), '<|>' , get_config_key('data', 'maxkwcount', '20' ) )
    self.keyword.set_completion(self.pn_completion.completion)
    evtmap = { "show_about" :  self.show_about_cb, \
    "on_pnote_destroy": self.do_exit, \
    "on_pnote_close": self.on_pnote_close, \
    "do_new_note": lambda o: pnote_new.PnoteNew(self.app).w.show_all(), \
    "do_show_pref": self.do_show_pref, \
    "do_export": self.do_export, \
    "do_export_selected": self.do_export_selected, \
    "do_import": self.do_import, \
    "do_export_html": self.do_export_html, \
    "do_send_mail": self.do_send_mail, \
    "do_print": self.do_print, \
    "bt_clear_button_press": self.bt_clear_button_press, \
    "on_keyword_activated": lambda o: self.do_search(self.keyword.get_text()), \
    "do_search": self.do_search_cb, \
    "on_result_list_row_activated": self.on_result_list_row_activated, \
    "on_result_list_start_interactive_search": self.on_result_list_start_interactive_search, \
    "on_result_list_key_press": self.on_result_list_key_press, \
    'on_setup_mail': lambda o: MailPref(self.app).run() ,\
    'do_export_selected_html': self.do_export_selected_html,\
    }
    statusbar = self.statusbar = self.wTree.get_widget("statusbar")
    msgid = statusbar.push(1, " welcome to pnote")
    result_list = self.result_list = self.wTree.get_widget("result_list")
    result_list_model = self.result_list_model = gtk.ListStore(int, str,str,str) # first col str as using int causing problems; data returning from db sometimes as str. pysqlite buggy?
    result_list.set_model(result_list_model)
    result_list.set_headers_visible(True)
    renderer = gtk.CellRendererText()
    #col1 = gtk.TreeViewColumn("ID", renderer, text=0)
    col2 = gtk.TreeViewColumn("Title", renderer,text=1)
    col3 = gtk.TreeViewColumn("Date", renderer,text=2)
    col4 = gtk.TreeViewColumn("Database", renderer,text=3)
    #col1.set_resizable(True)
    col2.set_resizable(True)
    col3.set_resizable(True)
    col2.set_max_width(250)
    col2.set_min_width(200)
    col3.set_min_width(200)
    col4.set_min_width(200)
    #result_list.append_column(col1)
    result_list.append_column(col2)
    result_list.append_column(col3)
    result_list.append_column(col4)
    result_list.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
    result_list.set_search_column(0)
    self.wTree.signal_autoconnect(evtmap)
    self.keyword.grab_focus()
  
  def on_result_list_key_press(self, o=None, e=None, d=None):
    #print gtk.gdk.keyval_name(e.keyval)
    if gtk.gdk.keyval_name(e.keyval) == 'Delete':
      selection = o.get_selection()
      if selection.count_selected_rows() == 1: # safe delete, only delete one note
        model, paths = selection.get_selected_rows() # get_selected() not available in SELECTION_MULTIPLE mode
        note_id = model.get_value(model.get_iter(paths[0]), 0)
        dbname = model.get_value(model.get_iter(paths[0]), 3)
        self.dbcon.execute("delete from " + dbname + ".lsnote where note_id = (?)" , ( note_id,  ) ) #the traling , is python stupid, forces it to be a tuple
        self.dbcon.commit()
        self.do_search(self.keyword.get_text())

  def bt_clear_button_press(self, obj, evt):
    if evt.button == 1: self.do_clear_keyword()
    else: self.bt_clear_popup_menu(evt)

  def bt_clear_popup_menu(self, evt):
    list_flags = get_config_key('data', 'list_flags', 'TODO|IMPORTANT|URGENT').split('|')
    menu_flags  = gtk.Menu()
    for fl in list_flags:
      if not fl == '':
        menuitem1 = gtk.MenuItem('List ' + fl)
        tmpstr = "lambda m,o: o.do_search( 'FLAGS:' + '{0}' ) ".format(fl)
        menuitem1.connect('activate', eval(tmpstr), self )
        menu_flags.append(menuitem1)
        menuitem1.show()
    menu_flags.popup(None, None, None, evt.button, evt.time, data=None)

  def on_pnote_close(self, obj, data=None):
      self.save_config()
      self.w.destroy()
      del self.app.pnmain
      return True

  def show_about_cb(self, obj, data=None):
    abt = gtk.AboutDialog()
    abt.set_name('pnote')
    abt.set_comments('a note management program. Ported from lsnote')
    abt.set_authors(['Steve Kieu <msh.computing@gmail.com>'])
    response = abt.run()
    abt.destroy()
      
  def save_config(self): save_config_key('data', 'keywords', self.pn_completion.get_list_str() )
              
  def do_exit(self, obj=None, data=None): # Exit here will NOT save the dbpath to teh config file
    print "Destroy called"
    self.save_config()
    gtk.main_quit()
    
  def do_show_pref(self, obj, data=None): Preference().w.show_all()
    
  def do_export(self,obj, data=None): pass
    
  def do_export_selected(self, obj, data=None):    pass
    
  def do_import(self,obj, data=None):    pass

  def do_export_html(self, obj, data=None):    pass
  
  def do_export_selected_html(self,o): pass
  
  def get_list_notes_from_selection(self):
    list_notes = []
    def func(model, path, iter):
      note_id = model.get_value(model.get_iter(path), 0)
      dbname =  model.get_value(model.get_iter(path), 3)
      list_notes.append([dbname, note_id])
    self.result_list.get_selection().selected_foreach(func)
    return  list_notes
    
  def do_send_mail(self, obj, data=None):
    alert_mail_to = get_text_from_user('Recipient', 'Enter list of recipient separated by ;', size = 300)
    if alert_mail_to != None:
      list_notes = self.get_list_notes_from_selection()
      for item in list_notes:
        tmpk = item[0]+str(item[1])
        if tmpk in self.app.note_list: mynote = self.app.note_list[tmpk]
        else: mynote = pnote_new.PnoteNew(self.app, item[1], item[0])
        send_note_as_mail(note = mynote, mail_from = get_config_key('data', 'mail_from', 'none'), to = alert_mail_to )
      
  def do_print(self, obj, data=None):    pass
    
  def do_clear_keyword(self, obj=None):
    self.keyword.set_text('')
    self.keyword.grab_focus()
    
  def do_search(self, keyword):
    sqlcmd = ''
    if not self.keyword.get_text() == keyword: self.keyword.set_text(keyword)
    self.result_list_model.clear()
    rcount = 0
    for dbname in dict.keys(self.app.dbpaths):
      if (keyword.startswith(r'^')):
          # Execute arbitrary sql
          sqlcmd = keyword[1:]
      elif keyword.startswith('FLAGS:'):
        mykeys = keyword[5:].split(':')
        mykeys = [ x for x in mykeys if not x == '' ]
        sqlcmd = "select * from {0}.lsnote where".format(dbname)
        for i in xrange(len(mykeys)):
          kw = mykeys[i].strip()
          sqlcmd += (r" AND " if (i > 0) else " ") + r" flags like '%" + kw + r"%' "

      else:
          # Parse & as and
          kwlist = keyword.split(r'&')
          sqlcmd = "select * from {0}.lsnote ".format(dbname)
          kwlist = [ x for x in kwlist if not x == '' ]
          for i in xrange(len(kwlist)):
              kw = kwlist[i].strip()
              sqlcmd += (r" AND " if (i > 0) else " WHERE ") + r" (title like '%" + kw + r"%' OR url like '%" + kw + "%' OR content like '%" + kw + "%' ) "

      if sqlcmd.startswith('select '): sqlcmd += " order by timestamp desc, note_id desc LIMIT " + get_config_key('data', 'SELECT_LIMIT', '250')
      dbc = self.dbcon.cursor()
      try:
        dbc.execute(sqlcmd) #; print sqlcmd
        if sqlcmd.startswith('select '):
          while (True): # Isn't it do: while hahaha
              row = dbc.fetchone()
              if (row == None): break
              rcount+=1
              try: self.result_list_model.append([(row['note_id']),(row['title']),(row['datelog']), dbname])
              except Exception as e: print e[0]
        else: self.dbcon.commit()        
      except Exception as e: print e # sql exec error
    self.statusbar.push(1, " Found " + str(rcount) + " note" + ('s' if (rcount > 1) else '' ) + r'!')
    dbc.close()
    
    if not keyword == '': self.pn_completion.add_entry(keyword)
      
  def do_search_cb(self, obj, data=None):
      self.do_search(self.keyword.get_text())

  def on_result_list_row_activated(self, obj, path, view_col, data=None):
    model = obj.get_model()
    note_id = model.get_value(model.get_iter(path), 0) # col1 -> note_id
    dbname = model.get_value(model.get_iter(path), 3)
    try: self.app.note_list[dbname+str(note_id)].w.present()
    except Exception as e: pnote_new.PnoteNew(self.app, note_id, dbname).w.show_all()
    
  def on_result_list_start_interactive_search(self, obj, data=None): pass


if __name__ == "__main__":
    try:
     dbpath = sys.argv[1]
     print "Using database file ", dbpath
     if dbpath:
      app = pnmain(dbpath)
      gtk.main()
     else:
      print "Database file path needed\nUsage: ", sys.argv[0] , "path_to_db_file"
      os.exit()
    except:
     dbpath = '/home/sk/tmp/clt.db'
     app = pnmain(dbpath)
     app.w.show_all()
     gtk.main()
     #print "Database file path needed\nUsage: ", sys.argv[0] , "path_to_db_file"

