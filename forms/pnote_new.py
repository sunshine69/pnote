#!/usr/bin/env python
# -*- coding: utf-8 -*-

# A new note

import os, sqlite3, time, shlex, subprocess, cPickle, random, StringIO
# from datetime import datetime # tzinfo, timedelta

try:
 import pygtk 
 pygtk.require('2.0')
except:
 pass
 
try:
 import gtk, pango #, gobject
 import gtk.glade
except:
 pass
  
from utils import *
  
class PnoteNew:
 
  def __init__(self,pnote_app, note_id = None, dbname = 'main'):
    self.app = pnote_app
    self.unique_num = 0
    self.window_size = get_config_key('pnote_new', 'window_size','0x0') # 0x0 default size
    self.dbname = dbname
    gladefile = "glade/pnote_new.glade"
    windowname = "pnote_new"
    self.wTree = gtk.glade.XML(gladefile)
    w = self.w = self.wTree.get_widget(windowname)
    if not self.window_size == '0x0':
      width,height = self.window_size.strip().split('x')
      try: self.w.resize(int(width),int(height))
      except Exception as e:
        print e
        print "Unable to resize window. Reset to default"
        self.window_size = '0x0'
    evtmap = { "on_pnote_new_destroy": self.destroy, \
    "on_bt_flag_button_press": self.on_bt_flag_button_press, \
    'on_bt_format_button_press': self.on_bt_format_button_press, \
    'on_bt_search_button_press': self.on_bt_search_button_press, \
    'on_bt_update_button_press': self.on_bt_update_button_press, \
    'on_bt_show_main_button_press': self.on_bt_show_main_button_press, \
    'on_bt_url_button_press': self.on_bt_url_button_press, \
    'on_bt_save_activate': lambda o: self.do_save(), \
    'on_bt_cancel_activate': self.on_bt_cancel_activate, \
    'on_bt_reminder_toggled': self.on_bt_reminder_toggled, \
    'on_bt_send_clicked': self.on_bt_send_clicked, \
    'on_edit_changed': self.on_edit_changed, \
    'on_bt_ro_toggled': self.on_bt_ro_toggled, \
    'on_show_noteinfo': self.on_show_noteinfo, \
    'on_end_update': self.on_end_update, \
    'on_delete_note': self.on_delete_note, \
    'on_filter_selection': self.on_filter_selection, \
    'on_filter_selection_newnote': lambda o: self.on_filter_selection(o, 'NEW_NOTE') ,\
    'on_pnote_new_key_press_event': self.on_pnote_new_key_press_event,\
    'on_insert_img': lambda o: self.insert_pixbuf_at_cursor() ,\
    'do_save_txt': lambda o: self.do_save_insert_txt(do='save'), \
    'do_insert_from': lambda o: self.do_save_insert_txt(do='insert') ,\
    'on_content_delete_from_cursor': self.on_content_delete_from_cursor,\
    'do_save_html': self.do_save_html ,\
    }
    statusbar = self.statusbar = self.wTree.get_widget("statusbar")
    self.bt_ro = self.wTree.get_widget('bt_ro')
    bt_flag = self.wTree.get_widget('bt_flag')
    bt_flag.set_image(gtk.image_new_from_file('icons/clear_left.png'))
    bt_format = self.wTree.get_widget('bt_format')
    bt_format.set_image(gtk.image_new_from_file('icons/kcoloredit.png'))
    bt_search = self.wTree.get_widget('bt_search')
    bt_search.set_image(gtk.image_new_from_file('icons/clear_left.png'))
    bt_update = self.wTree.get_widget('bt_update')
    bt_update.set_image(gtk.image_new_from_file('icons/kate.png'))
    bt_show_main = self.wTree.get_widget('bt_show_main')
    bt_show_main.set_image(gtk.image_new_from_file('icons/cookie.png'))
    bt_url = self.wTree.get_widget('bt_url')
    bt_url.set_image(gtk.image_new_from_file('icons/kgpg.png'))
    bt_reminder = self.wTree.get_widget('bt_reminder')
    title = self.title = self.wTree.get_widget('title')
    datelog = self.datelog = self.wTree.get_widget('datelog')
    flags = self.flags = self.wTree.get_widget('flags')
    content = self.content = self.wTree.get_widget('content')
    content.get_buffer().connect('modified-changed', self.content_changed_cb)
    url = self.url = self.wTree.get_widget('url')
    self.dbcon = self.app.dbcon
    # Create a tag table and add it with fixed list of attribute tags to be use later
    tag_tab = content.get_buffer().get_tag_table()
    tag_highlight = gtk.TextTag('highlight')
    tag_highlight.set_property('background_gdk' ,  gtk.gdk.color_parse('#FFD900') )
    tag_underline = gtk.TextTag("underline")
    tag_underline.set_property('underline', pango.UNDERLINE_SINGLE)
    tag_strikethrough = gtk.TextTag("strikethrough")
    tag_strikethrough.set_property('strikethrough', True)
    tag_start_update = gtk.TextTag('start_update')
    tag_start_update.set_property('foreground-gdk', gtk.gdk.color_parse('#FF8928') )
    tag_end_update = gtk.TextTag('end_update')
    tag_end_update.set_property('foreground-gdk', gtk.gdk.color_parse('#2B52FF') )
    # Load note_content if note_id
    for tg in [tag_highlight, tag_underline, tag_strikethrough, tag_start_update, tag_end_update]: tag_tab.add(tg)
    content.set_tabs(pango.TabArray(4,False))
    self.note_id = note_id
    self.readonly = 0
    self.econtent = ''
    self.timestamp = int(time.time())
    self.reminder_ticks = 0
    self.alert_count = 0
    self.last_kword = None
    self.note_search_backword = False
    self.pixbuf_dict_fromdb = dict()
    self.pixbuf_dict = dict()
    self.format_tab = [] # list of 3-tuples markname, markname, 'tagnames|property'
    if not note_id == None:
      dbc = self.dbcon.cursor()
      sql = "select * from {0}.lsnote WHERE note_id = {1}".format(self.dbname, self.note_id)
      #print sql
      dbc.execute(sql)
      try:
        row = dbc.fetchone()
        title.set_text(row['title'])
        self.w.set_title(row['title'][0:30])
        datelog.set_text(row['datelog'])
        flags.set_text(row['flags'])
        content.get_buffer().set_text(row['content'])
        self.content.get_buffer().set_modified(False)
        url.set_text('' if row['url'] == None else row['url'] )
        self.readonly = row['readonly']
        self.timestamp = row['timestamp']
        self.econtent = (row['econtent'] if not row['econtent'] == None else '')
        self.reminder_ticks = row['reminder_ticks']
        self.alert_count = row['alert_count']
        self.pixbuf_dict_fromdb = cPickle.loads(row['pixbuf_dict'])
        if not self.reminder_ticks == 0:
          bt_reminder.set_active(True)
        self.app.note_list[self.dbname+str(note_id)] = self
        self.load_pixbuf()# before format
        self.load_format_tag(row['format_tag'])
        if self.readonly == 1:
          self.content.set_editable(False)
          self.bt_ro.set_label('ro')
          self.bt_ro.set_active(True)
      except Exception as e: print e
      self.wTree.get_widget('bt_cancel').set_label('_Close')
      self.start_time = 0
      dbc.close()
    else:
      self.start_time = int(time.time())
      self.datelog.set_text(time.strftime("%d-%m-%Y %H:%M"))
    self.wTree.signal_autoconnect(evtmap)
    content.grab_focus()
    
  def on_bt_send_clicked(self, o=None): send_note_as_mail(self)
  
  def do_save_html(self, o=None):
    htmltext = "<html><head><title>{0}</title></head><body>{1}</body></html>".format(self.title.get_text(),  self.dump_to_html() )
    self.do_save_insert_txt(do='save', text = htmltext )
    
  def dump_to_html(self): # TODO For now Just like this
    buf = self.content.get_buffer()
    return "<PRE>{0}</PRE>".format(buf.get_text(buf.get_start_iter(), buf.get_end_iter() ) )
    #stringIO = StringIO()
    #itr = buf.get_start_iter()
    #while True:
      #marks = itr.get_marks()
      #for mark in marks:
        #for format_sec in self.format_tab:
          #if mark in format_sec:
            
  
  def do_save_insert_txt(self, do='save', text = None, urlpath = None):
    if urlpath == None:
      chooser = gtk.FileChooserDialog(title='Type new file name or select file',action=gtk.FILE_CHOOSER_ACTION_SAVE, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
      chooser.set_current_folder(self.app.filechooser_dir)
      ffilter = gtk.FileFilter(); ffilter.add_pattern('*.txt'); ffilter.set_name('txt')
      ffilter1 = gtk.FileFilter(); ffilter1.add_pattern('*.*'); ffilter1.set_name('All files')
      for ff in [ffilter, ffilter1]: chooser.add_filter(ff)
      res = chooser.run()
      if res == gtk.RESPONSE_OK:
        urlpath =  chooser.get_filename()
        self.app.filechooser_dir = chooser.get_current_folder()
      chooser.destroy()
    buf = self.content.get_buffer()
    if do == 'save':
      if os.path.isfile(urlpath):
          if get_text_from_user('Warning',"Over-writting existing file?\n\n", default_txt = None) != 0: return True
      if text == None: text = buf.get_text(buf.get_start_iter(), buf.get_end_iter())
      with open(urlpath,'wb') as fp: fp.write( text )
    else:
      with  open(urlpath,'rb') as fp: buf.insert_at_cursor(fp.read())

  def on_content_delete_from_cursor(self,o, delete_type, count ):
    buf = self.content.get_buffer()
    cur_iter = buf.get_iter_at_mark(buf.get_insert())
    if cur_iter.get_pixbuf() == None: return False
    mymarks = cur_iter.get_marks()
    for mykey in dict.keys(self.pixbuf_dict):
      for mark in mymarks:
        if mark in self.pixbuf_dict[mykey]:
          self.pixbuf_dict[mykey].remove(mark)
          if len(self.pixbuf_dict[mykey]) == 0: del self.pixbuf_dict[mykey]
    return False
              
  def load_pixbuf(self):
    buf = self.content.get_buffer()
    for urlpath in dict.keys(self.pixbuf_dict_fromdb):
      if os.path.isfile(urlpath):
        try: pixbuff = gtk.gdk.pixbuf_new_from_file(urlpath)
        except: continue
        for pos in self.pixbuf_dict_fromdb[urlpath]:
          itr = buf.get_iter_at_offset(pos)
          m1 = buf.create_mark(None, itr, True)
          try: self.pixbuf_dict[urlpath].append(m1)
          except: self.pixbuf_dict[urlpath] = [m1]
          buf.insert_pixbuf(itr, pixbuff )
    self.pixbuf_dict_fromdb = None
            
  def insert_pixbuf_at_cursor(self, urlpath=None):
    if urlpath == None:
      chooser = gtk.FileChooserDialog(title=None,action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
      chooser.set_current_folder(self.app.filechooser_dir)
      ffilter = gtk.FileFilter();ffilter.add_pixbuf_formats(); ffilter.set_name('Images')
      chooser.add_filter(ffilter)
      res = chooser.run()
      if res == gtk.RESPONSE_OK:
        urlpath =  chooser.get_filename()
        self.app.filechooser_dir = chooser.get_current_folder()
      chooser.destroy()
    if os.path.isfile(urlpath):
      try: pixbuff = gtk.gdk.pixbuf_new_from_file(urlpath)
      except: return True
      buf = self.content.get_buffer()
      itr = buf.get_iter_at_mark(buf.get_insert() )
      m1 = buf.create_mark(None, itr, True)
      buf.insert_pixbuf(itr, pixbuff)
      try: self.pixbuf_dict[urlpath].append(m1)
      except: self.pixbuf_dict[urlpath] = [m1]

  def dump_pixbuf_dict(self):
    output = dict()
    buf = self.content.get_buffer()
    for urlpath in dict.keys(self.pixbuf_dict):
      for im in self.pixbuf_dict[urlpath]:
        pos = buf.get_iter_at_mark(im).get_offset()
        try: output[urlpath].append(pos)
        except: output[urlpath] = [pos]
    return cPickle.dumps(output, cPickle.HIGHEST_PROTOCOL)
        
  def on_pnote_new_key_press_event(self,o=None, e=None ):
    if e.state & gtk.gdk.CONTROL_MASK:
      if gtk.gdk.keyval_name(e.keyval) == 'f':
        try: self.note_search.w.present()
        except:
          self.note_search =  NoteSearch(self)
          self.note_search.w.show_all()
      elif gtk.gdk.keyval_name(e.keyval) == 'h':
        msg = "What? you need help? :-)\nJust use your common sense, hover the mouse to each small button on the right to see what it does and right click for menu, etc.\nCtrl+f to search text within the note. Press F3 to search again\nThe export, print function not implemented yet, I will do later\nBest luck"
        message_box('Oh my god', msg)
        return True
    elif gtk.gdk.keyval_name(e.keyval) == 'F3':
      try: self.note_search.do_search()
      except:
        self.note_search =  NoteSearch(self)
        self.note_search.do_search()
    
  def build_flags_menu(self):
    list_flags = get_config_key('data', 'list_flags', 'TODO|IMPORTANT|URGENT').split('|')
    menu_flags  = gtk.Menu()
    sep = gtk.SeparatorMenuItem()
    menu_flags.append( sep )
    sep.show()
    for fl in list_flags:
      if not fl == '':
        menuitem = gtk.MenuItem('Flag as ' + fl)
        tmpstr = "lambda m,o: o.flags.set_text( o.flags.get_text() + ':' + '{0}' ) ".format(fl)
        menuitem.connect('activate', eval( tmpstr ) , self )
        menu_flags.prepend(menuitem)
        menuitem.show()
        menuitem1 = gtk.MenuItem('List ' + fl)
        tmpstr = "lambda m,o: o.app.show_main().do_search( 'FLAGS:' + '{0}' ) ".format(fl)
        menuitem1.connect('activate', eval(tmpstr), self )
        menu_flags.append(menuitem1)
        menuitem1.show()
    sep1 = gtk.SeparatorMenuItem()
    clear_flags = gtk.MenuItem('Clear all flags')
    clear_flags.connect('activate', lambda o: self.flags.set_text('')  )
    add_flag = gtk.MenuItem('Add new flag')
    add_flag.connect('activate', self.add_flag )
    remove_flag = gtk.MenuItem('Remove old flag')
    remove_flag.connect('activate', self.remove_flag )
    for i in (sep1, clear_flags, add_flag, remove_flag):
      menu_flags.append(i)
      i.show()
    return menu_flags
  def remove_flag(self, o=None):
    fname = get_text_from_user('Flag name', 'Enter flag name to remove from the list: ')
    list_flags = get_config_key('data', 'list_flags').split('|')
    try:
      list_flags.remove(fname)
      save_config_key('data', 'list_flags', "|".join(list_flags) )
    except: message_box("Information", "Error. Flasg does not exist" )
    
  def add_flag(self, o=None):
    fname = get_text_from_user('Flag name', 'Enter new flag name: ')
    save_config_key('data', 'list_flags', get_config_key('data', 'list_flags') + '|' + fname )
  
  def on_show_noteinfo(self, o=None):
    msg = "note_id: {0}\nLast update: {1}\nDatabase name: {2}\nDatabase file path: {3}\n".format(self.note_id, time.ctime(self.timestamp), self.dbname, self.app.dbpaths[self.dbname] )
    NoteInfo(self, msg).w.show_all()

  def on_delete_note(self, o):
    msg = "Are you sure to delete this note?"
    t_flags = self.flags.get_text()
    if not t_flags == '': msg += "\nThis note marked as " + t_flags
    d = gtk.MessageDialog(None, 0, gtk.MESSAGE_WARNING, gtk.BUTTONS_YES_NO, msg)
    r = d.run()
    if r == gtk.RESPONSE_YES:
      try:
        self.dbcon.execute("delete from "+self.dbname + ".lsnote where note_id = (?)", (self.note_id, ) )
        self.dbcon.commit()
        del self.app.note_list[self.dbname + str(self.note_id)]
      except Exception as e:  print e
      self.content.get_buffer().set_modified(False)
      self.w.destroy()
      
    d.destroy()
        
  def on_bt_ro_toggled(self, o, d=None):
    self.content.get_buffer().set_modified(True) # save
    if o.get_active():
      self.content.set_editable(False)
      self.bt_ro.set_label('ro')
      self.readonly = 1
    else:
      self.content.set_editable(True)
      self.bt_ro.set_label('rw')
      self.readonly = 0
      
  def on_edit_changed(self, o=None, d=None): self.content.get_buffer().set_modified(True)
  def on_bt_format_button_press(self, obj, evt, data=None):
    if evt.button == 1:
      buf = self.content.get_buffer()
      try: s,e = buf.get_selection_bounds()
      except: return
      buf.apply_tag_by_name('highlight', s,e)
      (m1,m2) = (buf.create_mark( None, s, True), buf.create_mark( None, e, True ) )
      self.format_tab.append([m1,m2,['highlight'], buf.get_text(s,e)[0:30].strip() ] )
      buf.set_modified(True)
      #TODO modified the format dict marks name -> tag list name
    elif evt.button == 3:
      FormatNote(self).w.show_all()
    
  def on_bt_search_button_press(self, obj, evt, data=None):
    if evt.button == 1:
      try:
        buf = self.content.get_buffer()
        start, end = buf.get_selection_bounds()
        inputstr = buf.get_text(start, end)
        if not inputstr == '': self.app.show_main().do_search(inputstr)
      except Exception as e: print e
    elif evt.button == 3: self.wTree.get_widget('menu_search').popup(None, None, None, evt.button, evt.time, data=None)
    

  def on_filter_selection(self, o, d = None):
    try:
      buf = self.content.get_buffer()
      start, end = buf.get_selection_bounds()
      inputstr = buf.get_text(start, end)
      if not inputstr == '':
        cmd = get_text_from_user("Command", "Enter command to process: ", "perl -ne ", int(get_config_key('data', 'dialog_entercommand_size', '350') ) )
        if not cmd == None:
          p1 = subprocess.Popen(shlex.split(cmd), stdin = subprocess.PIPE, stdout = subprocess.PIPE )
          result = p1.communicate(inputstr)[0]
          if d == 'NEW_NOTE':
            new_note = PnoteNew(self.app, None, self.dbname)
            new_note.content.get_buffer().set_text(result)
            new_note.w.show_all()
          else:
            buf.delete(start, end)
            buf.insert_interactive(start, result, self.content.get_editable())
    except: pass    

  def on_bt_update_button_press(self, obj, evt, data=None):
    if evt.button == 1:
      if self.start_time == 0: self.start_time = int(time.time())
      start_date = time.strftime("%A %d %B %Y %H:%M:%S")
      tex = "\n=======================\nUpdate: {0}".format(start_date)
      buf = self.content.get_buffer()
      s = buf.get_iter_at_mark(buf.get_insert() )
      m1 = buf.create_mark(None, s, True )
      buf.insert_with_tags_by_name(s, tex, 'start_update')
      e = buf.get_iter_at_mark(buf.get_insert() )
      m2 = buf.create_mark(None, e, True )
      self.format_tab.append( [m1, m2, ['start_update'], start_date ] )
      buf.insert_at_cursor("\n")
      self.content.scroll_to_mark(buf.get_insert() ,0 )
      self.content.grab_focus()
    elif evt.button == 3:
      pmenu = self.wTree.get_widget('menu_update')
      pmenu.popup(None, None, None, evt.button, evt.time, data=None)
        
  def on_end_update(self, o=None):
    if not self.start_time == 0:
      period = "%02d:%02d" % divmod((int(time.time()) - self.start_time), 60)
      end_date = time.strftime("%A %d %B %Y %H:%M:%S")
      tex = "\nEnd Update: {0}\nLength(min): {1}".format(end_date , period )
      buf = self.content.get_buffer()
      s = buf.get_iter_at_mark(buf.get_insert() )
      m1 = buf.create_mark(None, s, True )
      buf.insert_with_tags_by_name(s, tex, "end_update")
      self.content.scroll_to_mark(buf.get_insert(), 0)
      e = buf.get_iter_at_mark(buf.get_insert() )
      m2 = buf.create_mark(None, e, True )
      self.format_tab.append( [m1, m2, ['end_update'], end_date ] )
      self.start_time = 0
      buf.insert_at_cursor("\n")
      self.content.scroll_to_mark(buf.get_insert() ,0 )
      self.content.grab_focus()
    else: message_box('Information', "You need to start Update mark first")
        
  def on_bt_show_main_button_press(self, obj, evt, data=None):
    if evt.button == 1: self.app.show_main()
    elif evt.button == 3: pass #TODO show note info (last update time, list of book marks and can jump to it, etc)
  
  def on_bt_url_button_press(self, obj, evt, data=None):
    if evt.button == 1:
      try: self.e_content.w.present()
      except: self.e_content = EContent(self); self.e_content.w.show_all()
    elif evt.button == 3:
      chooser = gtk.FileChooserDialog(title="Select file to add to path",action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
      chooser.set_select_multiple(True)
      chooser.set_current_folder(self.app.filechooser_dir)
      res = chooser.run()
      if res == gtk.RESPONSE_OK:
        fname = chooser.get_filename()
        oldname = self.url.get_text()
        self.url.set_text( (fname if oldname == '' else oldname + '<|>' + fname )  )
        self.app.filechooser_dir = chooser.get_current_folder()
      chooser.destroy()
      
  def on_bt_cancel_activate(self,  evt, data=None):
    self.content.get_buffer().set_modified(False) # Tell do_save not to save
    self.destroy()

  def on_bt_reminder_toggled(self, o, data=None):
    if o.get_active(): NoteReminder(self).w.show_all()
    else: self.reminder_ticks = 0; self.alert_count = 0; self.content.get_buffer().set_modified(True)
    
  def content_changed_cb(self, texbuf): self.wTree.get_widget('bt_cancel').set_label('_Cancel')
  def load_format_tag(self, data):
    if data == None or data == '': return
    buf = self.content.get_buffer()
    templist = cPickle.loads(data)
    for item in templist:
      s,e,tagnames = item[0], item[1], item[2]
      its, ite  = buf.get_iter_at_offset(s), buf.get_iter_at_offset(e) 
      for tag in tagnames:
        if tag == 'None': buf.remove_all_tags(its,ite)
        elif tag.find('|') == -1: buf.apply_tag_by_name(tag, its, ite)
        else:
          (tgname, tgattr, tgvalue) = map(str.strip, tag.split('|') )
          tag = gtk.TextTag(tgname)
          buf.get_tag_table().add(tag)
          if tgvalue.find('#') == -1: tag.set_property(tgattr, tgvalue)
          else: tag.set_property(tgattr,gtk.gdk.color_parse(tgvalue) )
          buf.apply_tag(tag, its, ite)
      self.format_tab.append( [ buf.create_mark(None, its), buf.create_mark(None, ite), tagnames ] + item[3:] )
      
  def dump_format_tag(self):
    buf = self.content.get_buffer()
    def cvt(ar):
      buf = self.content.get_buffer()
      return [ buf.get_iter_at_mark(ar[0]).get_offset(),  buf.get_iter_at_mark(ar[1]).get_offset() ] + ar[2:]
    templist =  map(cvt, self.format_tab )
    return cPickle.dumps(templist, cPickle.HIGHEST_PROTOCOL)
      
  def do_save(self, d=None):
    if self.content.get_buffer().get_modified():
      sql = ''
      texbuf = self.content.get_buffer()
      tex = texbuf.get_text(texbuf.get_start_iter(), texbuf.get_end_iter() )
      if self.title.get_text() == '': self.title.set_text(tex[0:50].split("\n")[0].replace("\r",' ') )
      try:
        dbc = self.dbcon.cursor()
        if self.note_id == None:
          dbc.execute("insert into " + self.dbname + ".lsnote(title, datelog, flags, content, url, readonly, timestamp, format_tag, econtent, reminder_ticks, alert_count, pixbuf_dict) values((?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?) )", (self.title.get_text(), self.datelog.get_text(), self.flags.get_text(), tex, self.url.get_text(), self.readonly, int(time.time()), self.dump_format_tag(), sqlite3.Binary(self.econtent), self.reminder_ticks, self.alert_count, self.dump_pixbuf_dict() ) )
        else:
          dbc.execute("update " + self.dbname + ".lsnote set title = (?), datelog = (?), flags = (?), content = (?), url = (?), readonly = (?), timestamp = (?), format_tag = (?), econtent = (?), reminder_ticks = (?), alert_count = (?), pixbuf_dict = (?) where note_id = (?)", ( self.title.get_text(), self.datelog.get_text(), self.flags.get_text(), tex, self.url.get_text(), self.readonly, int(time.time()) , self.dump_format_tag() , sqlite3.Binary(self.econtent) , self.reminder_ticks , self.alert_count, self.dump_pixbuf_dict(), self.note_id ) )
        if not dbc.lastrowid == None:
          self.note_id = dbc.lastrowid
          self.app.note_list[self.note_id] = self
        self.dbcon.commit()
        self.content.get_buffer().set_modified(False)
        self.wTree.get_widget('bt_cancel').set_label('_Close')
        dbc.close()
      except Exception as e: print e
    else: print "Not modified. No save"
    if not d is None:
      if not 'NO_SAVE_SIZE' in d: self.save_window_size()
    else: self.save_window_size()
    self.w.set_title(self.title.get_text()[0:30])
    
  def on_bt_flag_button_press(self, obj, evt, data=None):
    if evt.button == 3: # Right click 3; Midle : 2; Left : 1
      self.build_flags_menu().popup(None, None, None, evt.button, evt.time, data=None)
    elif evt.button == 1: self.flags.set_text(self.flags.get_text()+":TODO")
    return True # Stop passing this event here
    
  def save_window_size(self):
    w,h = self.w.get_size()
    self.window_size = str(w)+'x'+str(h)
    save_config_key('pnote_new', 'window_size', self.window_size)
    
  def destroy(self, obj=None, data=None):
    if not data == None: pass
    else: self.do_save({'NO_SAVE_SIZE':1}) # If saved here, race condition will reset size to default
    try: del self.app.note_list[self.dbname + str(self.note_id)]
    except Exception as e: pass #print e.args[0]
    self.w.destroy()
    self.wTree = None
    return True
    
  def do_export(self,obj=None, data=None):    pass
  def do_import(self,obj=None, data=None):    pass
  def do_print_preview(self, obj=None, data=None):  pass
  def do_send_mail(self,obj=None, data=None):   pass
  def do_print(self, obj=None, data=None):  pass
  def do_search(self, obj=None, data=None):   pass
    
if __name__ == '__main__':
 PnoteNew().w.show()
 gtk.main()
