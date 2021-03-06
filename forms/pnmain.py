#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement 
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

import sqlite3, types, cPickle, base64, threading, subprocess
from forms import pnote_new
from utils import *

class pnmain:
  
  def __init__(self, dbpath, pnote_app=None):
    self.app = pnote_app
    self.dbpath = dbpath
    self.dbcon = self.app.db_setup()
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
    "do_send_mail": self.do_send_mail, \
    "do_print": self.do_print, \
    "bt_clear_button_press": self.bt_clear_button_press, \
    "on_keyword_activated": self.do_search_cb, \
    "do_search": self.do_search_cb, \
    "on_result_list_row_activated": self.on_result_list_row_activated, \
    "on_result_list_start_interactive_search": self.on_result_list_start_interactive_search, \
    "on_result_list_key_press": self.on_result_list_key_press, \
    'on_setup_mail': lambda o: MailPref(self.app).run() ,\
    'on_toolbar_menu': self.on_toolbar_menu,\
    'on_toolbar_menu_clicked': self.on_toolbar_menu_clicked, \
    'do_check_mail': self.on_check_mail, \
    'on_bt_find_button_release_event': self.on_bt_find_button_release_event,\
    'on_run_vacuum': lambda o: self.dbcon.cursor().execute('VACUUM'),\
    'on_sync_db': lambda o: self.sync_sqlite_db(),\
    'on_sync_db_baseid': lambda o: self.sync_sqlite_db(ask_base_id = True), \
    'on_run_script': lambda o: self.run_script() ,\
    'on_result_list_button_press_event': self.on_result_list_button_press_event, \
    }
    statusbar = self.statusbar = self.wTree.get_widget("statusbar")
    msgid = statusbar.push(1, " welcome to pnote")
    result_list = self.result_list = self.wTree.get_widget("result_list")
    result_list_model = self.result_list_model = gtk.ListStore(int, str,str,str)
    result_list.set_model(result_list_model)
    result_list.set_headers_visible(True)
    renderer = gtk.CellRendererText()
    #col1 = gtk.TreeViewColumn("ID", renderer, text=0)
    col2 = gtk.TreeViewColumn('Title'  , renderer,text=1)
    col3 = gtk.TreeViewColumn("Last Update", renderer,text=2)
    col4 = gtk.TreeViewColumn( "Database", renderer,text=3)
    #col1.set_resizable(True)
    col2.set_resizable(True)
    col3.set_resizable(True)
    col2.set_max_width(350)
    col2.set_min_width(200)
    col3.set_min_width(200)
    col4.set_min_width(200)
    #result_list.append_column(col1)
    result_list.append_column(col2)
    result_list.append_column(col3)
    result_list.append_column(col4)
    result_list.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
    result_list.set_search_column(0)
    self.bt_menu = self.wTree.get_widget('toolbar_menu'); self.bt_menu.set_menu(gtk.Menu())
    self.search_mode = 'note'
    self.imapdata = None
    self.tempdata = dict() # to store wany temporal data
    win_pos = get_config_key('data', 'pnmain_win_pos', '0:0')
    wx,wy = win_pos.split(':')
    if wx != '0' and wy != '0': self.w.move(int(wx), int(wy))
    if (get_config_key('global', 'run_startup_cmds', 'no') == 'yes' ):
        startup_cmds = get_config_key('global', 'startup_cmds', '').split('<|>')
        for _cmds in startup_cmds: self.run_script(file_name = _cmds)
    else:
        save_config_key('global', 'run_startup_cmds', 'no')
    self.wTree.signal_autoconnect(evtmap)
    self.keyword.grab_focus()

  def test_dlg(self):
      if not self.app.is_checking_mail:
          self.app.is_checking_mail = True
          self.app.checkmail(server=None if self.search_mode=='note' else self.search_mode )
          self.app.is_checking_mail = None

  def on_check_mail(self, evt, data=None):
      threading.Thread(target = self.test_dlg).start()

  def run_script(self, file_name = None):
      if file_name == None:
          chooser = gtk.FileChooserDialog(title="Select script to run or type command to run",action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
          chooser.set_current_folder(self.app.filechooser_dir)
          file_name = None
          res = chooser.run()
          if res == gtk.RESPONSE_OK:
            file_name =  chooser.get_filename()
            self.app.filechooser_dir = chooser.get_current_folder()
          chooser.destroy()
      elif file_name == '': return
      if os.path.isfile(file_name):
        subp = subprocess.Popen(shlex.split(file_name), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
      else:
        cmds = os.path.basename(file_name); print cmds
        subp = subprocess.Popen(shlex.split(cmds), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
      threading.Thread(target = lambda: subp.wait() ).start()
      self.app.list_popen.append(subp)
      
  def sync_sqlite_db(self, ask_base_id = False):
    remote_syncdb = get_config_key('data', 'remote_syncdb', 'none')
    if remote_syncdb == 'none' or ask_base_id:
      chooser = gtk.FileChooserDialog(title="Select second database file to sync with",action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
      chooser.set_current_folder(self.app.filechooser_dir)
      ffilter = gtk.FileFilter(); ffilter.add_pattern('*.db'); ffilter.set_name('db')
      ffilter1 = gtk.FileFilter(); ffilter1.add_pattern('*.sqlite3'); ffilter1.set_name('sqlite3 Database')
      ffilter2 = gtk.FileFilter(); ffilter2.add_pattern('*.*'); ffilter2.set_name('All files')
      chooser.add_filter(ffilter);chooser.add_filter(ffilter1);chooser.add_filter(ffilter2)
      res = chooser.run()
      if res == gtk.RESPONSE_OK:
        remote_syncdb =  chooser.get_filename()
        save_config_key('data', 'remote_syncdb', remote_syncdb)
        self.app.filechooser_dir = chooser.get_current_folder()
      chooser.destroy()
      
    if remote_syncdb != '' and os.path.isfile(remote_syncdb):
      if ask_base_id: last_sync_id = get_text_from_user('pnote - Enter', 'Endter base id you want to sync ', get_config_key('data', 'last_sync_id', '') )
      else:
          last_sync_timestamp = get_config_key('data', 'last_sync_timestamp', int(time.time()) - 86400 )
      from pdbsync import DbSync
      remote_con = sqlite3.connect(remote_syncdb)
      if ask_base_id:
            sync_it_now = DbSync(self.app.dbcon, remote_con, base_id = int(last_sync_id) - int(get_config_key('data', 'count_notes_sync', '250')) )
      else:
          sync_it_now = DbSync(self.app.dbcon, remote_con, timestamp = int(last_sync_timestamp), DEBUG = True )
      sync_it_now.do_sync()
      if ask_base_id:
            save_config_key('data', 'last_sync_id', sync_it_now.last_sync_id)
            save_config_key('data', 'last_sync_timestamp', int(time.time()) )
      else: save_config_key('data', 'last_sync_timestamp', last_sync_timestamp)
      message_box('pnote - Information', sync_it_now.return_msg)
      
  def on_bt_find_button_release_event(self, o=None, evt=None):
    if evt.button == 1: self.do_search_cb(o,evt)
    else:
      thismenu = gtk.Menu()
      server = self.search_mode
      if server != 'note':
        imapconn = None
        try:
          imapconn = self.app.imapconn[server]
          imapconn.select(readonly=1)
        except:
              self.app.load_list_imap_acct(connect=True, server=self.search_mode, locking = False)
              try: imapconn = self.app.imapconn[server]
              except: pass
        list_imap_account = self.app.list_imap_account_dict
        pn_imap = PnImap(self.app, imapconn)
        if pn_imap.get_mailboxes() != 'OK': return
        for mailbox in pn_imap.mailboxes:
            if not mailbox == '':
              menuitem1 = gtk.CheckMenuItem(mailbox)
              _tmp_func = eval("lambda m,o, fl_text=mailbox: o.set_current_mailbox (fl_text)" )
              menuitem1.connect('activate', _tmp_func, self, mailbox )
              if mailbox == self.app.current_mailbox: menuitem1.set_active(True)
              thismenu.append(menuitem1)
              menuitem1.show()
        menuitem1 = gtk.CheckMenuItem('ALL')
        _tmp_func = eval("lambda m,o, fl_text=mailbox: o.set_current_mailbox (fl_text)" )
        menuitem1.connect('activate', _tmp_func, self, None )
        thismenu.append(menuitem1); menuitem1.show()
        thismenu.popup(None, None, None, evt.button, evt.time, data=None)
              
  def   set_current_mailbox(self, text): self.app.current_mailbox = text
  
  def display_new_mail(self, data = None):
    import email
    _data = data# { 'iserver' :  [conn,  [(msgID, 'text'),(msgID, 'text')] ] } 
    self.imapdata = _data
    self.result_list_model.clear()
    self.tempdata['mail']=dict()
    _count = 0
    for iserver in dict.keys(_data):
      self.search_mode=iserver
      if _data[iserver][1] != None:
        for (_target, msgID, msgData) in _data[iserver][1]:
          _mail_msg_header = email.message_from_string(msgData)
          _iter = self.result_list_model.append([int(msgID), _mail_msg_header.get('SUBJECT'), iserver, _target])
          self.list_tooltip = PnTips(self.result_list.get_column(0), self.tempdata['mail'], 0)
          self.list_tooltip.add_view(self.result_list)
          self.tempdata['mail'][msgID] = _mail_msg_header
          self.tempdata['mail']['TIP_' + msgID] = "From: %s\nDate: %s" % (_mail_msg_header.get('FROM'), _mail_msg_header.get('DATE'))
          _path = self.result_list_model.get_path(_iter)
          self.bt_menu.set_label(iserver.split('.')[-2])
          _count += 1

    self.statusbar.push(1, " Found " + str(_count) + " message" + ('s' if (_count > 1) else '' ) + r'!')
  def on_toolbar_menu(self,bt=None):
    thismenu = gtk.Menu()
    list_imap_account = self.app.list_imap_account_dict
    for fl in dict.keys(list_imap_account):
        if not fl == '':
          menuitem1 = gtk.MenuItem(fl)
          _tmp_func = eval("lambda m,o, fl_text=fl: o.do_set_search_mode( fl_text ) " )
          menuitem1.connect('activate', _tmp_func, self, fl )
          thismenu.append(menuitem1)
          menuitem1.show()
    bt.set_menu(thismenu)
    
  def do_set_search_mode(self, modestr=''):
    self.bt_menu.set_label(modestr.split('.')[-2] )
    self.search_mode = modestr
    
  def on_toolbar_menu_clicked(self,o=None):
    self.bt_menu.set_label('NoteDB')
    self.search_mode = 'note'
    self.tempdata['mail'] = None
    #self.list_tooltip.disable() #TODO we dont not display tooltip for note. Do we need it at all?
    try:
      self.list_tooltip.remove_view()
      self.list_tooltip = None
    except: pass  

  def create_menu_on_result_list(self, data=None):
    # Run aggregate functions etc on list of selected notes
    (model, paths) = data
    #List comprehension woa. At least split first one to make it easier to read
    list_id_dbname = [ (model[path][0], model[path][3]) for path in [ path_t[0] for path_t in paths ] ]
    def calculate_total_time_spent(obj=None):
      msg = "Total time in minute: %2d:%2d" % divmod(sum([ get_a_note(app= self.app,note_id = _temp[0], dbname = _temp[1] )['time_spent'] for _temp in list_id_dbname ]), 60)
      message_box('pnote - Total time spent', msg)

    def run_sql(obj=None):
      sql = get_text_from_user('pnote - Enter', "Enter sql command to execute. I will append WHERE|AND note_id in (id1, id2, ..)\nExample: update %s.lsnote set flags = 'New flasg'\nThe %s is required (be replaced by actual dbname)")
      if sql != '' and sql != None:
        no_error = True
        for _id, dbname in list_id_dbname:
          sql1 = sql % dbname
          if sql1.find('where') != -1 or sql1.find('WHERE') != -1:
                  sql1 = "%s AND note_id = %s" % (sql1, _id)
          else:
                sql1 = "%s where note_id = %s" % (sql1, _id)
          try: self.app.dbcon.execute(sql1)
          except Exception, e:
            no_error = False
            message_box('pnote - error', "Sorry there is error: %s" % e)
        if no_error:
          self.app.dbcon.commit()
          message_box('pnote - success', 'Operation completed successfuly')
    
    def do_save_to_webnote(obj=None):
    	list_notes = self.get_list_notes_from_selection()
      	for item in list_notes:
        	tmpk = item[0]+str(item[1])
        	if tmpk in self.app.note_list: mynote = self.app.note_list[tmpk]
        	else: mynote = pnote_new.PnoteNew(self.app, item[1], item[0])
		save_to_webnote(mynote)

    # Add MORE Funtion to process here
    # end  
    menu = gtk.Menu()
    menuitem0 = gtk.MenuItem("Save to webnote")
    menuitem0.connect('activate', do_save_to_webnote)
    menu.append(menuitem0); menuitem0.show()
    menuitem1 = gtk.MenuItem("Display total time spent")
    menuitem1.connect('activate', calculate_total_time_spent)
    menu.append(menuitem1); menuitem1.show()
    menuitem2 = gtk.MenuItem("Run sql on these notes")
    menuitem2.connect('activate', run_sql )
    menu.append(menuitem2); menuitem2.show()
    return menu
    
  def on_result_list_button_press_event(self, treeview, event):
     if event.button == 3:
         # Figure out which item they right clicked on
         path = treeview.get_path_at_pos(int(event.x),int(event.y))
         # Get the selection
         selection = treeview.get_selection()
         # Get the selected path(s)
         rows = selection.get_selected_rows() # rows is (model, array_of_paths) , again a path is a tuple
         # If they didnt right click on a currently selected row, change  the selection
         if path[0] not in rows[1]:
             selection.unselect_all()
             selection.select_path(path[0])
         if selection.count_selected_rows() > 1:
             #popup multiple selection menu
             self.create_menu_on_result_list(rows).popup(None, None, None, event.button, event.time, data=None)
         else:
             #popup single selection box
             self.create_menu_on_result_list(rows).popup(None, None, None, event.button, event.time, data=None)
         return True

      
  def on_result_list_key_press(self, o=None, e=None, d=None):
    #print gtk.gdk.keyval_name(e.keyval)
    if gtk.gdk.keyval_name(e.keyval) == 'Delete':
      if self.search_mode == 'note':
          selection = o.get_selection()
          if selection.count_selected_rows() == 1: # safe delete, only delete one note
            model, paths = selection.get_selected_rows() # get_selected() not available in SELECTION_MULTIPLE mode
            #note_id = model.get_value(model.get_iter(paths[0]), 0)
            note_id = model[paths[0]][0]
            #dbname = model.get_value(model.get_iter(paths[0]), 3)
            dbname = model[paths[0]][3]
            self.dbcon.execute("delete from " + dbname + ".lsnote where note_id = (?)" , ( note_id,  ) ) #the traling , is python stupid, forces it to be a tuple
            self.dbcon.commit()
            self.do_search(self.keyword.get_text())
      else:#TODO Shoule we allow to delete mail message
        if get_text_from_user('Warning',"Are you sure to delete this message?\n\n", default_txt = None) != 0: return
        data = self.imapdata
        selection = o.get_selection()
        if selection.count_selected_rows() == 1: # safe delete, only delete one note
          model, path = selection.get_selected_rows() # get_selected() not available in SELECTION_MULTIPLE mode
          #msgID =  model.get_value(model.get_iter(path[0]), 0)
          msgID = model[path[0]][0]
          #iserver =  model.get_value(model.get_iter(path[0]), 2)
          iserver = model[path[0]][2]
          conn = data[iserver][0]
          #_target =  model.get_value(model.get_iter(path[0]), 3)
          _target = model[path[0]][3]
          try: conn.select(_target,readonly=0)
          except:
            self.app.load_list_imap_acct(connect = True, server = iserver, locking = False)
            conn = self.app.imapconn[iserver]
            conn.select(_target,readonly=0)
          print "DEBUG, gonna delete msgID ", msgID  
          conn.store(msgID, '+FLAGS', '(\Deleted)')
        
  def bt_clear_button_press(self, obj, evt):
    if evt.button == 1: self.do_clear_keyword()
    else: self.bt_clear_popup_menu(evt)

  def bt_clear_popup_menu(self, evt):
    list_flags = get_config_key('data', 'list_flags', 'TODO<|>IMPORTANT<|>URGENT').split('<|>')
    menu_flags  = gtk.Menu()
    for fl in list_flags:
      if not fl == '':
        menuitem1 = gtk.MenuItem('List ' + fl)
	myself = self
        tmpstr = "lambda m,o: o.do_search( 'FLAGS:' + '%s' ) " % (fl)
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
      
  def save_config(self):
    save_config_key('data', 'keywords', self.pn_completion.get_list_str() )
    
  def do_exit(self, obj=None, data=None): # Exit here will NOT save the dbpath to teh config file
    self.save_config()
    self.app.do_exit(flag='from_pnmain')
    
  def do_show_pref(self, obj, data=None): Preference(app=self.app).w.show_all()
    
  def get_list_notes_from_selection(self):
    list_notes = []
    def func(model, path, iter):
      #note_id = model.get_value(model.get_iter(path), 0)
      #dbname =  model.get_value(model.get_iter(path), 3)
      note_id = model[path][0]
      dbname = model[path][3]
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
      
  def do_print(self, obj, data=None): pass
    
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
      elif (keyword.startswith(r'sql:')):
      	  sqlcmd = keyword[4:]
      elif keyword.startswith('FLAGS:'):
        mykeys = keyword[5:].split(':')
        mykeys = [ x for x in mykeys if not x == '' ]
        sqlcmd = "select note_id, title, timestamp from %s.lsnote where" % dbname
        for i in xrange(len(mykeys)):
          kw = mykeys[i].strip()
          sqlcmd += (r" AND " if (i > 0) else " ") + r" flags like '%" + kw + r"%' "

      else:
          # Parse & as and
          kwlist = keyword.split(r'&')
          sqlcmd = "select note_id, title, timestamp from %s.lsnote " % dbname
          kwlist = [ x for x in kwlist if not x == '' ]
          for i in xrange(len(kwlist)):
              kw = kwlist[i].strip()
              sqlcmd += (r" AND " if (i > 0) else " WHERE ") + r" (title like '%" + kw + r"%' OR url like '%" + kw + "%' OR content like '%" + kw + "%' ) "

      if sqlcmd.startswith('select '): sqlcmd += " order by timestamp desc, note_id desc LIMIT " + get_config_key('data', 'SELECT_LIMIT', '250')
      dbc = self.dbcon.cursor()
      try:
        #print sqlcmd      
        dbc.execute(sqlcmd)
        if sqlcmd.startswith('select '):
          while (True): # Isn't it do: while hahaha
              row = dbc.fetchone()
              if (row == None): break
              rcount+=1
              try: self.result_list_model.append([(row['note_id']),(row['title']),time.strftime("%d %b %Y %H:%M", time.gmtime(row['timestamp'])) , dbname])
              except Exception , e: print e[0]
        else: self.dbcon.commit()        
      except Exception , e: print e # sql exec error
    self.statusbar.push(1, " Found " + str(rcount) + " note" + ('s' if (rcount > 1) else '' ) + r'!')
    dbc.close()
    
    if not keyword == '': self.pn_completion.add_entry(keyword)
      
  def do_search_cb(self, obj, data=None):
      if self.bt_menu.get_label() == 'NoteDB': self.search_mode == 'note'
      if (self.search_mode == 'note'): self.do_search(self.keyword.get_text())
      else:
        try:
          imapconn = self.app.imapconn[self.search_mode]
          imapconn.select(readonly = 1) # try to make sure all okay
        except:
          self.app.load_list_imap_acct(connect=True, server = self.search_mode, locking = False)
          imapconn = self.app.imapconn[self.search_mode]
        if imapconn:
          pn_imap = PnImap(self.app, imapconn)
          _search_result = pn_imap.search_mail(self.keyword.get_text())
          if len(_search_result) > 0:
            _data = {self.search_mode :  [imapconn,  _search_result ] }
            self.display_new_mail(data = _data)
          else: print "search return empty"  

  def on_result_list_row_activated(self, obj, path, view_col, data=None):
    model = obj.get_model()
    if self.search_mode == 'note':
      #note_id = model.get_value(model.get_iter(path), 0) # col1 -> note_id
      note_id = model[path][0]
      #dbname = model.get_value(model.get_iter(path), 3)
      dbname = model[path][3]
      try: self.app.note_list["%s_%s" % (dbname,str(note_id))].w.present()
      except Exception , e: pnote_new.PnoteNew(self.app, note_id, dbname).w.show_all()
    else:
        data = self.imapdata
        #msgID =  model.get_value(model.get_iter(path), 0)
        msgID = model[path][0]
        #iserver =  model.get_value(model.get_iter(path), 2)
        iserver = model[path][2]
        conn = data[iserver][0]
        #_target =  model.get_value(model.get_iter(path), 3)
        _target = model[path][3]
        conn.select(_target,readonly=0)
        (ret, mesginfo) = conn.uid("FETCH", msgID , '(BODY[1] FLAGS)' )
        #_title = model.get_value(model.get_iter(path), 1)
        _title = model[path][1]
        _date = self.tempdata['mail'][str(msgID)].get('DATE')
        _url = self.tempdata['mail'][str(msgID)].get('FROM')
        _flags = mesginfo[0][0][mesginfo[0][0].find('FLAGS'):mesginfo[0][0].find('UID')].strip()
        _newnote = pnote_new.PnoteNew(self.app)
        _content = mesginfo[0][1]
        _html2text_cmd = get_config_key('global', 'html2text_cmd', 'None')
        if _html2text_cmd == 'None':
          from html2text import html2text
          _content = html2text(_content.decode('utf-8') )
        else:
          _content = TextFormatter(html2text = _html2text_cmd).run_html2text(_content)  
        #from htmlrender import render
        #_content = render(_content)# Got trouble with some html text (error)
        #from html2txt import HtmlToText
        #_content = HtmlToText(_content).out.output_text # not better than html2text slower and code ugly. Doesn't not provide new line and structured text
        _newnote.content.get_buffer().insert_at_cursor(_content)
        _newnote.title.set_text(_title)
        _newnote.datelog.set_text(_date)
        _newnote.url.set_text(_url)
        _newnote.flags.set_text(_flags)
        _newnote.w.show_all()
    
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

