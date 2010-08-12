#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Main application. Read, Load config

import os,sys
if sys.platform=="win32":
  [ gtkdir ] = [ x  for x in os.getenv('PATH').split(';') if x.find('GTK') != -1 ]
  os.environ['PATH'] += ";%s/../lib;%s" % (gtkdir, gtkdir)
  
sys.path.append(sys.path[0])
os.chdir(sys.path[0])

import pygtk, gtk, gobject
import ConfigParser, sqlite3

SETTINGS = gtk.settings_get_default()

if sys.platform=="win32": SETTINGS.set_long_property("gtk-button-images", True, "main")

# Can not import * here not sure why
# This u do not need to put one pnmain more when instantiate the object. forms.pnmain means read file pnmain.py under forms dir when sourcing it, import symbol pnmain (which is a class; that is why when instantiate can use symbol pnmain only
#from forms.pnmain import pnmain
#from forms.PnoteNew import PnoteNew
# This needs one more PnoteNew when instantiate the object. Buggar !. This import the symbol as pnmain.py but not sourcing it yet. That is why needs more pnmain.pnmain
from forms import pnmain, pnote_new
from utils import *
from clipboard import PnClipboard

class pnote:
   
  def __init__(self, dbpath=None):
    self.cipherkey = None
    self.filechooser_dir = os.getcwd()
    self.working_mode = get_config_key('global', 'working_mode', 'note')
    if dbpath == None:
      dbpath = get_config_key('data', 'main_db_path')
      if dbpath == '':
        dbpath = self.selectdb()
        if not os.path.isfile(dbpath): dbpath = run_setup(dbpath)
    self.dbpath = dbpath
    self.dbpaths = { 'main': dbpath }
    self.dbcon = None
    self.note_list = {}
    dbpathstr = get_config_key('data', 'db_paths', 'None')
    if not dbpathstr == 'None':
      i = 0
      for p in dbpathstr.split('|'):
        if (not p == '') and (not p == 'None') and (not p == None): self.dbpaths['sub' + str(i)] = p
        i += 1
    
    ic=gtk.status_icon_new_from_file('icons/cookie.png')
    ic.connect("popup-menu", self.icon_popup_menu)
    ic.connect("activate", lambda o: pnote_new.PnoteNew(self).w.show_all() )
    self.load_list_imap_acct()
    gobject.timeout_add_seconds(int(get_config_key('data', 'reminder_timer_interval', '60') ), self.query_note_reminder )
    self.clipboards = PnClipboard()

  def load_list_imap_acct(self):
    list_imap_account_str = get_config_key('global', 'list_imap_account','')
    if list_imap_account_str != '': self.list_imap_account_dict = cPickle.loads(base64.b64decode( list_imap_account_str ) )
    else: self.list_imap_account_dict = dict()
    
  def change_passwd(self):
    if self.cipherkey == None:
      if get_text_from_user('CRITICAL WARNING', "It seems you failed to unlock this field before. Changing password now AND if the password is not the same as the old correct one you will LOSE old information\nIf you still want to try to enter password to unlock this field, click Cancel, and then click Cancel in the popup window. Then click the lock button again\nIf you really want to DISCARD old information and reset to use newpass then click OK now", default_txt = None) != 0:
        message_box('Break', 'Aborted'); return
    newpass = get_text_from_user('New pass:', 'Enter new password:',show_char=False, completion = False, default_txt = 'none')
    if newpass != 'none': self.cipherkey = newpass
    else: message_box('Warning!','Password not changed')
    
  def query_note_reminder(self):
    for dbname in dict.keys(self.dbpaths):
      dbcon = self.db_setup()
      sql = "select note_id, alert_count from {0}.lsnote where reminder_ticks > 0 AND reminder_ticks <= {1}".format(dbname, int(time.time()) )
      cur = dbcon.cursor()
      cur.execute(sql)
      while (True):
        row = cur.fetchone()
        if (row == None): break
        note_id = row['note_id']
        try: self.note_list[dbname+str(note_id)].w.present()
        except: pnote_new.PnoteNew(self, note_id, dbname).w.show_all()
        alert_mail_to = get_config_key('data', 'alert_mail_to', 'none')
        if not alert_mail_to  == 'none':
          alert_count = row['alert_count']
          if alert_count == 0:
            send_note_as_mail(note = self.note_list[dbname+str(note_id)], mail_from = get_config_key('data', 'mail_from'), to = alert_mail_to )
            sql1 = "update {0}.lsnote set alert_count = {1} where note_id = {2}".format(dbname, alert_count + 1, note_id)
            dbcon.execute(sql1)
            dbcon.commit()
      cur.close()
    return True
          
  def show_main(self, obj=None, data=None):
    try: self.pnmain.w.present() # use w.window.show() in the FAQ not working
    except:
      print "Create new pnmain"
      self.pnmain = pnmain.pnmain(self.dbpath, self)
      self.pnmain.w.show_all()
    return self.pnmain

  def db_setup(self):
    """
    is called by other window/object in the application pnmain, PnoteNew etc
    """
    if self.dbcon != None: return self.dbcon
    try:
      dbcon = sqlite3.connect(self.dbpath)
      #dbc = dbcon.cursor()
      dbcon.row_factory = sqlite3.Row
      dbcon.text_factory = str # sqlite3.OptimizedUnicode
      if len(self.dbpaths) > 1:
        for dbname in dict.keys(self.dbpaths):
          if not dbname == 'main': dbcon.execute("attach database (?) as (?)", (self.dbpaths[dbname], dbname ))
      self.dbcon = dbcon
      return dbcon
    except Exception as e: print e; return False
        
  def icon_popup_menu(self, status_icon, button, activate_time, data=None):
    # popup menu
    ic_menu_tree = gtk.glade.XML('glade/icon_menu.glade')
    ic_menu = ic_menu_tree.get_widget('icon_menu')
    list_flags = get_config_key('data', 'list_flags', 'TODO|IMPORTANT|URGENT').split('|')
    for fl in list_flags:
      if not fl == '':
        menuitem = gtk.MenuItem('List ' + fl)
        _tmp_func = eval( "lambda m,o=self,kword=fl: o.show_main().do_search( 'FLAGS:' + kword ) " )
        menuitem.connect('activate', _tmp_func )
        ic_menu.prepend(menuitem)
        menuitem.show()
    _menu_sep = gtk.SeparatorMenuItem()
    ic_menu.prepend(_menu_sep)
    _menu_sep.show()
    clipboards = self.clipboards
    for clipinfo in clipboards.clipboard_history:
      if len(clipinfo.text) > 50: _label = clipinfo.text[0:47].split(os.linesep)[0] + ' ...'
      else: _label = clipinfo.text
      menuitem = gtk.MenuItem(_label)
      _tmp_func = eval("lambda m,cb=clipboards, cbi = clipinfo: cb.set_clipboard(cbi.text) " )
      menuitem.connect('activate', _tmp_func)
      ic_menu.prepend(menuitem)
      menuitem.show()
    
    ic_menu.popup(None, None, None, button, activate_time, data=None)
    evtmap = { 'icon_menu_show_main': self.show_main, \
      'do_app_exit': self.do_exit, \
      'show_recent_notes': self.show_recent_notes, \
    }
    ic_menu_tree.signal_autoconnect(evtmap)
    return True

  def show_recent_notes(self, obj, data=None):
    ncount = get_config_key('data', 'RECENT_NOTES_COUNT', '3')
    for dbname in dict.keys(self.dbpaths):
      sql = "select note_id from "+ dbname + ".lsnote order by timestamp desc limit " + ncount
      dbc = self.db_setup().cursor()
      dbc.execute(sql)
      while (True):
        r = dbc.fetchone()
        if r == None: break
        pnote_new.PnoteNew(self, r['note_id'], dbname).w.show_all()
      dbc.close()

  def do_exit(self, obj, data=None):
    save_config_key('data', 'main_db_path',self.dbpath)
    try: self.pnmain.do_exit()
    except: gtk.main_quit()

  def selectdb(self):
    chooser = gtk.FileChooserDialog(title="Select database file or enter new filename",action=gtk.FILE_CHOOSER_ACTION_SAVE, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
    res = chooser.run()
    dbpath =''
    if res == gtk.RESPONSE_OK:
      dbpath = chooser.get_filename()
      save_config_key('data', 'main_db_path', dbpath)
    chooser.destroy()
    return dbpath

if __name__ == "__main__":
  try:
     dbpath = sys.argv[1]
     print "Using database file ", dbpath
     pnote(dbpath).show_main()
  except Exception as e:
    print e
    pnote().show_main()

  gtk.main()