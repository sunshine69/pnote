#!/usr/bin/env python

import pygtk,gtk,pango,gobject
import os, ConfigParser, random, sqlite3, time, threading, base64, cPickle
from random import randrange
from Crypto.Cipher import Blowfish

def get_text_from_user(title='Input text', msg = 'Enter text:', default_txt = '', size = -1, show_char = True, completion = True):
    d = gtk.Dialog(title, None, 0, (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK, gtk.RESPONSE_ACCEPT) )
    l = gtk.Label(msg); l.set_line_wrap(True)
    d.vbox.pack_start(l)
    l.show()
    if default_txt != None:
      e = gtk.Entry(); e.set_visibility(show_char)
      e.connect('activate', lambda o: d.response(gtk.RESPONSE_ACCEPT) )
      if not size == '':
        try: e.set_size_request(size ,-1)
        except: e.set_size_request(-1 ,-1)
      e.set_text(default_txt)
      recent_filter_cmd = get_config_key('data','recent_filter_cmd', '')
      maxcount_recent_filter_cmd = get_config_key('data','maxcount_recent_filter_cmd',  '20')
      if completion:
        pn_completion = PnCompletion(recent_filter_cmd, '<|>' , int(maxcount_recent_filter_cmd))
        e.set_completion(pn_completion.completion)
      d.vbox.pack_end(e)
      e.show()
    r = d.run()
    retval = None
    if r == gtk.RESPONSE_ACCEPT:
      if default_txt != None:
        retval = e.get_text().strip()
        if completion:
          pn_completion.add_entry(retval)
          if not save_config_key('data', 'recent_filter_cmd', pn_completion.get_list_str()): print "Error saving config"
      else: retval = 0
    else: retval = None
    d.destroy()
    return retval

def send_note_as_mail(note=None, mail_from = '', to='', subject = ''):
    forked_to_sendmail = get_config_key('data', 'mail_forked_send', 'no')
    if note == None: print "Need to pass me a note"; return
    mail_server = get_config_key('data','mail_server', 'newhost')
    if mail_server == 'newhost':
      response = MailPref(note.app).run()
      if response == 1: message_box('error','You need to setup mail first. rerun it to reconfigure'); return
      mail_server = get_config_key('data','mail_server')
    port = get_config_key('data', 'mail_port')
    mail_use_ssl = (True if get_config_key('data', 'mail_use_ssl').strip() == 'yes' else False )
    mail_use_auth = (True if get_config_key('data', 'mail_use_auth').strip() == 'yes' else False )
    if mail_use_auth:
      mail_user = get_config_key('data', 'mail_user')
      if not set_password(note.app): return 1
      mail_passwd = BFCipher(note.app.cipherkey).decrypt( base64.b64decode( get_config_key('data', 'mail_passwd') ) )
      if mail_passwd == None: message_box('error', 'Wrong password!'); return 1
    import smtplib
    import mimetypes
    from optparse import OptionParser
    from email import encoders
    from email.message import Message
    from email.mime.audio import MIMEAudio
    from email.mime.base import MIMEBase
    from email.mime.image import MIMEImage
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    COMMASPACE = ', '
    buf = note.content.get_buffer()
    if mail_from == '':
          me = get_config_key('data', 'mail_from', 'none')
          if me == 'none': me = get_text_from_user('From', 'From: '); save_config_key('data', 'mail_from', me)
    else: me = mail_from
    if to == '':
      to = get_text_from_user('To: ', 'Recipient address separated by ; ', size = 300)
      if to == None: message_box('error', 'Recipients required'); return
    pathstr = note.url.get_text()
    if pathstr != '':
        paths = pathstr.split('<|>')
        outer = MIMEMultipart()
        #msg = MIMEText( buf.get_text(buf.get_start_iter(), buf.get_end_iter()) )
        _subject = note.title.get_text()
        
        if _subject == '' or _subject == None:
          texbuf = note.content.get_buffer()
          _subject = texbuf.get_text(texbuf.get_start_iter(), texbuf.get_end_iter() )[0:50].split(os.linesep)[0].replace("\r",' ')
          
        outer['Subject'] = (_subject if subject == '' else subject)
        outer.attach( MIMEText(buf.get_text(buf.get_start_iter(), buf.get_end_iter()) , 'plain') )
        outer.preamble = 'You will not see this in a MIME-aware mail reader.\n'
        outer['From'] = me
        outer['To'] = to
        for path in paths:
          filename = os.path.split(path)[1]
          if os.path.isfile(path):
            ctype, encoding = mimetypes.guess_type(path)
            if ctype is None or encoding is not None: ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            if maintype == 'text':
                fp = open(path)
                # Note: we should handle calculating the charset
                msg = MIMEText(fp.read(), _subtype=subtype)
                fp.close()
            elif maintype == 'image':
                fp = open(path, 'rb')
                msg = MIMEImage(fp.read(), _subtype=subtype)
                fp.close()
            elif maintype == 'audio':
                fp = open(path, 'rb')
                msg = MIMEAudio(fp.read(), _subtype=subtype)
                fp.close()
            else:
                fp = open(path, 'rb')
                msg = MIMEBase(maintype, subtype)
                msg.set_payload(fp.read())
                fp.close()
                # Encode the payload using Base64
                encoders.encode_base64(msg)
            msg.add_header('Content-Disposition', 'attachment', filename=filename)
            outer.attach(msg)
    else:
      outer = MIMEText(buf.get_text(buf.get_start_iter(), buf.get_end_iter() ))
      outer['Subject'] = (note.title.get_text() if subject == '' else subject)
      outer['From'] = me
      outer['To'] = to
      
    def fork_send():
      try:
        if mail_use_ssl: mailer =  smtplib.SMTP_SSL(mail_server, port)
        else: mailer = smtplib.SMTP(mail_server, port)
        if mail_use_auth: mailer.login(mail_user, mail_passwd)
        mailer.sendmail(me, to.split(';'), outer.as_string())
        mailer.quit()
      except Exception as ex: print "send_note_as_mail Error: " , ex
    if forked_to_sendmail == 'no': print "Sending mail in main thread"; fork_send()
    else: print "Forked to send mail"; threading.Thread(target = fork_send).start()
    
def run_setup(dbpath=''):
  if dbpath == '':
    chooser = gtk.FileChooserDialog(title=None,action=gtk.FILE_CHOOSER_ACTION_SAVE, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
    res = chooser.run()
    if res == gtk.RESPONSE_OK: dbpath =  chooser.get_filename()
    chooser.destroy()
  if dbpath == '':
    message_box("You need to enter new file for the database")
    return False
  msg = "Setup new database at {0}. Click OK to proceed".format(dbpath)
  print msg
  message_box('Information', msg)
  conn = sqlite3.connect(dbpath)
  conn.executescript("""
  CREATE TABLE lsnote(note_id integer primary key, title varchar(254), datelog date, content text, url varchar(254), reminder_ticks unsigned long long default 0, flags text, timestamp integer, readonly integer default 0, format_tag BLOB, econtent BLOB, alert_count integer default 0, pixbuf_dict BLOB);
  create index reminder_ticks_idx on lsnote(reminder_ticks DESC);
  create index timestamp_idx on lsnote(timestamp DESC);
  """)
  conn.commit()
  msg = "Completed. if you set a new database file you can attached it by editing the config file in your {0}/.pnote/pnote.cfg".format(os.path.expanduser("~") )
  print msg
  message_box('Information', msg)
  return dbpath
  
def get_config_key(section='data',key='', default_val=''):
    if not os.path.exists(os.path.expanduser("~") + '/.pnote'): os.mkdir(os.path.expanduser("~") + '/.pnote')
    config = ConfigParser.RawConfigParser()
    config.read(os.path.expanduser("~") + '/.pnote/pnote.cfg')
    retval = ''
    def tmpfunc():
      try: config.add_section(section)
      except: pass
      config.set(section, key, default_val)
      with open(os.path.expanduser("~") + '/.pnote/pnote.cfg', 'wb') as configfile: config.write(configfile)
      return default_val
    try: retval = config.get(section, key).strip()
    except: retval = tmpfunc()
    if retval == '' or retval == None or retval == 'None': tmpfunc()
    return retval
      
def save_config_key(section='data', key='', value=''):
    config = ConfigParser.RawConfigParser()
    config.read(os.path.expanduser("~") + '/.pnote/pnote.cfg')
    try: config.set(section, key, value)
    except:
      try:
        config.add_section(section)
        config.set(section, key, value)
      except: return False
    with open(os.path.expanduser("~") + '/.pnote/pnote.cfg', 'wb') as configfile: config.write(configfile)
    return True      

def message_box(title = 'Message', msg = ''):
    d = gtk.MessageDialog(None, 0, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, msg)
    d.set_title(title)
    d.run()
    d.destroy()

#def swap_dict(original_dict): return dict([(v, k) for (k, v) in original_dict.iteritems()])

class BFCipher:
    def __init__(self, pword):
        self.__cipher = Blowfish.new(str(pword))
    def encrypt(self, file_buffer):
        ciphertext = self.__cipher.encrypt(self.__pad_file('OK' + file_buffer))
        return ciphertext
    def decrypt(self, file_buffer):
        cleartext = self.__depad_file(self.__cipher.decrypt(file_buffer))
        if cleartext.startswith('OK'): cleartext = cleartext[2:]
        else: cleartext = None
        return cleartext
    # Blowfish cipher needs 8 byte blocks to work with
    def __pad_file(self, file_buffer):
        pad_bytes = 8 - (len(file_buffer) % 8)                                 
        for i in xrange(pad_bytes - 1): file_buffer += chr(randrange(0, 256))
        # final padding byte; % by 8 to get the number of padding bytes
        bflag = randrange(6, 248); bflag -= bflag % 8 - pad_bytes
        file_buffer += chr(bflag)
        return file_buffer
    def __depad_file(self, file_buffer):
        pad_bytes = ord(file_buffer[-1]) % 8
        if not pad_bytes: pad_bytes = 8
        return file_buffer[:-pad_bytes]
          
class PnCompletion():
  
  def __init__(self, initial_list_str=None, separator = '<|>', max_entry_count='10'):
    self.completion = gtk.EntryCompletion()
    model = gtk.ListStore(str)
    self.completion.set_model(model)
    self.completion.set_text_column(0)
    self.completion.set_inline_completion(True)
    self.list_entry = set()
    self.max_entry_count = int(max_entry_count)
    self.separator = separator
    self.populate(initial_list_str)
    
  def populate(self, keywords):
    if keywords == '' or keywords == None: return
    kwlist = keywords.split(self.separator)
    self.last_entry = (kwlist[-1] if not kwlist[-1] == '' else kwlist[-2])
    for kw in kwlist:
      kw.strip()
      if not kw == '':
        self.list_entry.add(kw)
        self.completion.get_model().append([kw])

  def get_list_str(self):
    tmpstr = ''
    model = self.completion.get_model()
    fiter = model.get_iter_first()
    while (True):
        if fiter == None: break
        try: tmpstr += model.get_value(fiter,0) + self.separator
        except Exception as e: print "class: pCompletion: " + e # Not sure the first one value return None
        fiter = model.iter_next(fiter)
    return tmpstr

  def add_entry(self, keyword ):
    keyword_list = self.completion.get_model()
    self.last_entry = keyword
    if not keyword in self.list_entry:
      self.list_entry.add(keyword)
      keyword_list.append([keyword])
      kwcount = len(self.list_entry)
      if kwcount > self.max_entry_count:
        self.list_entry.remove(keyword_list.get_value(keyword_list.get_iter_first(),0))
        keyword_list.remove(keyword_list.get_iter_first())

class FormatNote:
  
  def add_tag_to_table(self, tagname, tag_property, value = '',flag = 'on', mark1=None, mark2=None, text = None):
    format_tab = self.PnoteNew.format_tab
    if tagname not in format_tab:
      format_tab[tagname] = [ {tag_property: value} , [ (flag, mark1, mark2, text) ] ]
    else:
      format_tab[tagname][0][tag_property]=value
      format_tab[tagname][1].append( (flag, mark1, mark2, text) )
  
  def create_unique_tagname(self):
    tagn = 'tag' + str(random.randint(0,100000) )
    while tagn in self.PnoteNew.format_tab: tagn = 'tag' + str(random.randint(0,100000) )
    return tagn
    
  def do_format(self, o=None):
    m1, m2 =  self.buf.create_mark(None, self.s , False), self.buf.create_mark(None, self.e, False )
    if self.cb_underline.get_active():
      tagn = self.create_unique_tagname()
      tag = gtk.TextTag(tagn)
      tag.set_property('underline', pango.UNDERLINE_SINGLE )
      self.buf.get_tag_table().add(tag)
      self.buf.apply_tag(tag, self.s,self.e)
      self.add_tag_to_table(tagn, 'underline', pango.UNDERLINE_SINGLE, 'on' , m1, m2)
    if self.cb_strike.get_active():
      tagn = self.create_unique_tagname()
      tag = gtk.TextTag(tagn)
      tag.set_property('strikethrough', True )
      self.buf.get_tag_table().add(tag)
      self.buf.apply_tag(tag, self.s,self.e)
      self.add_tag_to_table(tagn, 'strikethrough', True, 'on' ,m1, m2)
    if self.fontcolorset:
      color = self.bt_fontcolor.get_color()
      tagn = self.create_unique_tagname()
      tag = gtk.TextTag(tagn)
      tag.set_property('foreground-gdk', color)
      self.buf.get_tag_table().add(tag)
      self.buf.apply_tag(tag, self.s, self.e)
      self.add_tag_to_table(tagn,'foreground-gdk', color, 'on' ,m1, m2 )
    if self.bgcolorset:
      color = self.bt_bgcolor.get_color()
      tagn = self.create_unique_tagname()
      tag = gtk.TextTag(tagn)
      tag.set_property('background_gdk', color)
      self.buf.get_tag_table().add(tag)
      self.buf.apply_tag(tag, self.s, self.e)
      self.add_tag_to_table(tagn,'background_gdk', color, 'on' ,m1, m2 )
    if self.fontset:
      font_desc = self.bt_font.get_font_name()
      tagn = self.create_unique_tagname()
      tag = gtk.TextTag(tagn)
      tag.set_property('font', font_desc)
      self.buf.get_tag_table().add(tag)
      self.buf.apply_tag(tag, self.s,self.e)
      self.add_tag_to_table(tagn,'font', font_desc, 'on' ,m1, m2 )
      
    self.buf.set_modified(True)
    self.w.destroy()
      
  def do_cancel(self, o=None): self.w.destroy()
  def on_bt_fontcolor_color_set(self, o=None): self.fontcolorset = True
  def on_bt_bgcolor_color_set(self, o=None): self.bgcolorset = True
  def on_bt_font_font_set(self, o=None): self.fontset = True
  def on_bt_clear_clicked(self, o=None, d=None):
    if d == None:
      self.buf.remove_all_tags(self.s, self.e)
    elif d == 'CLEAR_ALL':
      s,e  =  self.buf.get_start_iter(), self.buf.get_end_iter() 
      self.PnoteNew.format_tab = dict()
      self.buf.remove_all_tags(s,e)
      
    self.buf.set_modified(True)
    self.w.destroy()
  def on_bt_clear_all_clicked(self,o=None): self.on_bt_clear_clicked(None, 'CLEAR_ALL')

  def destroy(self): self.w.destroy(); return True
  
  def __init__(self, PnoteNew = None):
    self.PnoteNew = PnoteNew
    self.wTree = gtk.glade.XML('glade/format_w.glade')
    w = self.w = self.wTree.get_widget('format_w')
    self.cb_underline = self.wTree.get_widget('cb_underline')
    self.cb_strike = self.wTree.get_widget('cb_strike')
    self.bt_fontcolor = self.wTree.get_widget('bt_fontcolor')
    self.bt_bgcolor = self.wTree.get_widget('bt_bgcolor')
    self.bt_font = self.wTree.get_widget('bt_font')
    self.fontcolorset = self.bgcolorset = self.fontset = False
    evtmap = { 'on_bt_cancel_activate': lambda o: self.destroy() ,\
      'destroy': lambda o: self.destroy,\
      'on_bt_apply_activate': self.do_format , \
      'on_bt_fontcolor_color_set': self.on_bt_fontcolor_color_set, \
      'on_bt_bgcolor_color_set': self.on_bt_bgcolor_color_set, \
      'on_bt_font_font_set': self.on_bt_font_font_set, \
      'on_bt_clear_clicked': self.on_bt_clear_clicked, \
      'on_bt_clear_all_clicked': self.on_bt_clear_all_clicked,\
    }
    self.buf = self.PnoteNew.content.get_buffer()
    try: self.s,self.e = self.buf.get_selection_bounds()
    except: return
    self.wTree.signal_autoconnect(evtmap)

class NoteInfo:

  def destroy(self): self.w.destroy(); return True
  
  def __init__(self, note, label = ''):
    self.note = note
    buf = self.note.content.get_buffer()
    self.wTree = gtk.glade.XML('glade/note_info.glade')
    self.w = self.wTree.get_widget('note_info')
    self.w.connect('destroy', lambda o: self.destroy() )
    self.wTree.get_widget('label_info').set_label(label)
    hbox_highlight = self.wTree.get_widget('hbox_highlight')
    hbox_update = self.wTree.get_widget('hbox_update')
    self.combo_list_highlight, self.combo_list_update = gtk.combo_box_new_text(), gtk.combo_box_new_text()
    hbox_highlight.pack_start(self.combo_list_highlight)
    hbox_update.pack_start(self.combo_list_update)
    self.highlight_dict = dict()
    self.highlight_dict['top'] = buf.create_mark(None, buf.get_start_iter() )
    self.highlight_dict['end'] = buf.create_mark(None, buf.get_end_iter() )
    self.update_dict = dict()
    self.combo_list_highlight.append_text('top')
    self.populate_combo()
    self.combo_list_highlight.append_text('end')
    #self.combo_list_highlight.set_active(0); self.combo_list_update.set_active(0)
    self.combo_list_highlight.connect('changed',self.on_combo_list_highlight_changed )
    self.combo_list_update.connect('changed',self.on_combo_list_update_changed)
    
  def on_combo_list_highlight_changed(self, o=None):
    m1 = self.highlight_dict[o.get_active_text()]
    self.note.content.scroll_mark_onscreen(m1)
    
  def on_combo_list_update_changed(self, o=None):
    m1 = self.update_dict[o.get_active_text()]
    self.note.content.scroll_mark_onscreen(m1)
  
  def populate_combo(self):
    format_tab = self.note.format_tab
    for item in format_tab:
      if item == 'highlight':
        for row in format_tab[item][1]:
          try:
            text = row[3]
            self.highlight_dict[text] = row[2]
            self.combo_list_highlight.append_text(text)
          except: pass  
      elif item == 'start_update':
        for row in  format_tab[item][1]:
          try:
            text = row[3]
            self.update_dict[text] = row[2]
            self.combo_list_update.append_text(text)
          except: pass
         
class NoteReminder:
  def destroy(self): self.w.destroy(); return True
  def __init__(self, note):
    self.note = note
    self.wTree = gtk.glade.XML('glade/note_reminder.glade')
    self.w = self.wTree.get_widget('note_reminder')
    self.w.connect('destroy', lambda o: self.destroy() )
    self.calendar = self.wTree.get_widget('calendar1')
    hbox_time = self.wTree.get_widget('hbox_time')
    self.hour = gtk.combo_box_entry_new_text(); self.minute = gtk.combo_box_entry_new_text()
    hbox_time.pack_start(self.hour); hbox_time.pack_start(gtk.Label(' h ') )
    hbox_time.pack_start(self.minute); hbox_time.pack_start(gtk.Label(' m') )
    for i in xrange(0,24): self.hour.append_text(str(i))
    for i in xrange(0,60,15): self.minute.append_text(str(i))
    evtmap = { 'on_bt_ok_clicked': self.on_bt_ok_clicked,\
    'on_bt_cancel_clicked': self.on_bt_cancel_clicked,\
    }
    y,m,d,H,M,S,wd,yd,isdst = time.localtime()
    self.calendar.select_month(m-1, y); self.calendar.select_day(d); self.hour.set_active(H); self.minute.set_active(0)
    self.wTree.signal_autoconnect(evtmap)
    
  def on_bt_ok_clicked(self,o=None):
    y,m,d = self.calendar.get_date()
    timestr = "{0}/{1}/{2} {3}:{4}".format(d, m+1, y, self.hour.get_active_text(), self.minute.get_active_text())
    self.note.reminder_ticks = time.mktime(time.strptime(timestr, "%d/%m/%Y %H:%M") )
    self.note.content.get_buffer().set_modified(True)
    self.w.destroy()

  def on_bt_cancel_clicked(self, o=None): self.w.destroy()
    
class Preference:
  def destroy(self): self.w.destroy(); return True
  def __init__(self):
    self.wTree = gtk.glade.XML('glade/preference.glade')
    self.w = self.wTree.get_widget('preferences')
    self.textview =   self.wTree.get_widget('textview1')
    evtmap = { 'on_bt_save_clicked': self.on_bt_save_clicked,\
    'on_bt_cancel_clicked':self.on_bt_cancel_clicked,\
    'destroy': lambda o: self.destroy() ,\
    }
    fp = open(os.path.expanduser("~") + '/.pnote/pnote.cfg', 'rb')
    buf = self.textview.get_buffer()
    buf.insert_at_cursor(fp.read())
    fp.close()
    self.textview.set_size_request(int(get_config_key('data', 'pref_wind_width','400') ), int(get_config_key('data', 'pref_wind_height', '300') ) )
    self.wTree.signal_autoconnect(evtmap)

  def on_bt_save_clicked(self, o=None):
    fp = open(os.path.expanduser("~") + '/.pnote/pnote.cfg', 'wb')
    buf = self.textview.get_buffer()
    fp.write(buf.get_text(buf.get_start_iter(), buf.get_end_iter()))
    fp.close()
    self.destroy()

  def  on_bt_cancel_clicked(self, o=None): self.destroy()

def set_password(app, change = False):
    retval = True
    if app.cipherkey == None or change:
      app.cipherkey = get_text_from_user('Password required','Enter password to lock/unlock config file', show_char=False, completion = False, default_txt = 'none')
      if app.cipherkey == 'none':
        if not change: app.cipherkey = None
        message_box('error', 'Aborted')
        retval = False
    return retval  

class MailPref:
  def destroy(self): self.w.destroy(); return self.response
  def __init__(self, app):
    self.app = app
    self.wTree = gtk.glade.XML('glade/mail_pref.glade')
    self.w = self.wTree.get_widget('window1')
    table1 = self.wTree.get_widget('table1')
    self.e_smpt_server = gtk.combo_box_entry_new_text();  self.e_smpt_server.show()
    table1.attach(self.e_smpt_server, 1, 2, 0, 1)
    self.e_port = self.wTree.get_widget('e_port')
    self.cbox_use_auth = self.wTree.get_widget('cbox_use_auth')
    self.e_username = self.wTree.get_widget('e_username')
    self.e_passwd = self.wTree.get_widget('e_passwd')
    self.cbox_use_ssl = self.wTree.get_widget('cbox_use_ssl')
    self.cbox_forked_mail = self.wTree.get_widget('cbox_forked_mail')
    self.bt_del_imap = self.wTree.get_widget('bt_del_imap')
    self.cbox_is_imap_server = self.wTree.get_widget('cbox_is_imap_server')
    self.bt_cancel = self.wTree.get_widget('bt_cancel')
    self.bt_del_imap.set_sensitive(False)
    evtmap = { 'on_bt_save_clicked': self.on_bt_save_clicked,\
    'on_button1_clicked':self.on_button1_clicked,\
    'destroy': lambda o: self.destroy() ,\
    'on_cbox_is_imap_server_toggled': self.on_cbox_is_imap_server_toggled,\
    'on_bt_del_imap_clicked': self.on_bt_del_imap_clicked,\
    }
    self.load_smtp_config()
    self.response = 1
    self.combo_handler_id = None
    self.combo_handler_id1 = None
    self.wTree.signal_autoconnect(evtmap)
    
  def on_cbox_is_imap_server_toggled(self,o=None):
    flag = self.cbox_is_imap_server.get_active()
    if flag:
      self.combo_handler_id = self.e_smpt_server.connect("changed", lambda o: self.list_server_changed(control = 'changed') )
      self.combo_handler_id1 = self.e_smpt_server.child.connect("activate", lambda o: self.list_server_changed(control = 'activate') )
      self.bt_del_imap.set_sensitive(True)
      self.load_server_list()
    else:
      self.e_smpt_server.disconnect(self.combo_handler_id)
      self.e_smpt_server.child.disconnect(self.combo_handler_id1)
      self.cbox_use_auth.set_sensitive(True)
      self.load_smtp_config()
    
  def load_server_list(self):
    self.e_smpt_server.get_model().clear()
    for account_name in dict.keys(self.app.list_imap_account_dict): self.e_smpt_server.append_text(account_name)
    self.e_smpt_server.set_active(0)
    
  def on_bt_del_imap_clicked(self,o=None):
    if (self.cbox_is_imap_server.get_active()):
      imap_server = self.e_smpt_server.get_active_text().strip()
      try:
        del self.app.list_imap_account_dict[imap_server]
        save_config_key('global', 'list_imap_account', base64.b64encode(cPickle.dumps(self.app.list_imap_account_dict, cPickle.HIGHEST_PROTOCOL)  ) )
        self.app.load_list_imap_acct()
        self.e_smpt_server.remove_text(self.e_smpt_server.get_active())
        self.e_smpt_server.child.set_text('')
      except: pass
    
  def list_server_changed(self,control=None):
    if (self.cbox_is_imap_server.get_active()):
      imap_server = self.e_smpt_server.get_active_text().strip()
      if control == 'activate': imap_account = self.app.list_imap_account_dict.get(imap_server,['','',False,''] )
      else: imap_account = self.app.list_imap_account_dict.get(imap_server )
      if imap_account != None:
        self.e_port.set_text(imap_account[3] )
        self.e_username.set_text(imap_account[0])
        self.cbox_use_ssl.set_active(imap_account[2])
        self.cbox_use_auth.set_active(True) # imap always requires auth, this refuse to confuse user
        self.cbox_use_auth.set_sensitive(False)
        self.bt_cancel.set_label('Cancel')
    else: self.load_smtp_config()
    self.bt_cancel.set_label('Cancel')
    
  def run(self): self.w.show_all(); return self.response
  
  def load_smtp_config(self):
    self.e_smpt_server.get_model().clear()
    self.e_smpt_server.append_text(get_config_key('data', 'mail_server', '') )
    self.e_smpt_server.set_active(0)
    self.e_port.set_text(get_config_key('data', 'mail_port', '25') )
    self.e_username.set_text(get_config_key('data', 'mail_user') )
    self.e_passwd.set_text('')
    self.e_passwd.set_visibility(False)
    self.cbox_use_ssl.set_active( (False if (get_config_key('data', 'mail_use_ssl', 'no') == 'no' ) else True )  )
    self.cbox_use_auth.set_active( (False if (get_config_key('data', 'mail_use_auth', 'no') == 'no' ) else True )  )
    self.cbox_forked_mail.set_active( (False if (get_config_key('data', 'mail_forked_send', 'no') == 'no' ) else True )  )
    
  def on_button1_clicked(self,o=None): self.response = 1; self.destroy()
  def on_bt_save_clicked(self,o=None):
    newpass = self.e_passwd.get_text(); encpass64 = None
    if newpass != '':
      if not set_password(self.app): return 1
      encpass = BFCipher(self.app.cipherkey).encrypt(newpass.strip() )
      encpass64 = base64.b64encode(encpass)
    if (self.cbox_is_imap_server.get_active()):
      imap_server = self.e_smpt_server.get_active_text().strip()
      self.e_smpt_server.append_text(imap_server)
      imap_account = self.app.list_imap_account_dict.get(imap_server, ['','',False,''])
      imap_account[0] = self.e_username.get_text().strip()
      if encpass64 != None: imap_account[1] = encpass64
      imap_account[2] = ( True if  self.cbox_use_ssl.get_active() else False )
      imap_account[3] = self.e_port.get_text().strip()
      self.app.list_imap_account_dict[imap_server] = imap_account
      save_config_key('global', 'list_imap_account', base64.b64encode(cPickle.dumps(self.app.list_imap_account_dict, cPickle.HIGHEST_PROTOCOL)  ) )
      self.load_server_list()
    else:
      save_config_key('data', 'mail_server', self.e_smpt_server.get_active_text().strip())
      save_config_key('data', 'mail_port', self.e_port.get_text().strip())
      save_config_key('data', 'mail_user', self.e_username.get_text().strip())
      if encpass64 != None: save_config_key('data', 'mail_passwd', encpass64 )
      save_config_key('data', 'mail_use_ssl', ( 'yes' if  self.cbox_use_ssl.get_active() else 'no' ) )
      save_config_key('data', 'mail_use_auth', ( 'yes' if  self.cbox_use_auth.get_active() else 'no' ) )
      save_config_key('data', 'mail_forked_send', ( 'yes' if  self.cbox_forked_mail.get_active() else 'no' ) )
      self.load_smtp_config()
    self.app.load_list_imap_acct()
    self.response = 0
    self.bt_cancel.set_label('Close')
    
class EContent:
  
  def destroy(self):
    self.w.destroy()
    self.note.e_content = None
    
  def __init__(self, note):
    self.note = note; self.app = note.app
    self.wTree = gtk.glade.XML('glade/e_content.glade')
    self.w = self.wTree.get_widget('w_econtent')
    evtmap = { 'on_bt_cancel_clicked': lambda o: self.destroy() ,\
    'destroy': lambda o: self.destroy(), \
    'on_bt_changepass_clicked': lambda o: self.app.change_passwd(), \
    'on_bt_save_clicked': self.on_bt_save_clicked,\
    }
    self.econtent = self.wTree.get_widget('tv_econtent')
    self.econtent.set_size_request(int(get_config_key('pnote_new', 'econtent.w', '300' ) ), int(get_config_key('pnote_new', 'econtent.h', '200') ) )
    self.load_content()
    self.wTree.signal_autoconnect(evtmap)

  def load_content(self):
    buf = self.econtent.get_buffer()
    if self.app.cipherkey == None or self.app.cipherkey == '':
      self.app.cipherkey = get_text_from_user(title='Input', msg='Enter password to lock/unlock:', show_char=False, completion=False )
      if self.app.cipherkey == None or self.app.cipherkey == '': self.econtent.set_editable(False); return
    if not self.note.econtent == '':
      bf = BFCipher(self.app.cipherkey)
      try:
        tex = bf.decrypt(self.note.econtent)
        if tex == None:
          self.app.cipherkey = None
          message_box('!!', 'Wrong password!')
          self.econtent.set_editable(False); return
        else: self.note.bt_url.set_image(gtk.image_new_from_file('icons/decrypted.png'))
        buf.insert_at_cursor(tex)
      except Exception, ex : print ex[0]
    
  def on_bt_save_clicked(self,o=None):
    buf = self.econtent.get_buffer()
    bf = BFCipher(self.app.cipherkey)
    tex = buf.get_text(buf.get_start_iter(), buf.get_end_iter() )
    self.note.econtent = bf.encrypt( tex )
    self.note.content.get_buffer().set_modified(buf.get_modified() )
    self.destroy()
    
class NoteSearch:
  
  def destroy(self):
    self.w.destroy()
    save_config_key('data', 'note_search_history', self.pn_completion.get_list_str())
    self.note.note_search = None
    return True
    
  def __init__(self, note):
    self.note = note
    self.wTree = gtk.glade.XML('glade/note_search.glade')
    self.w = self.wTree.get_widget('note_search')
    evtmap = { 'destroy': lambda o: self.destroy(),\
    'on_bt_find_clicked': lambda o: self.do_search(),\
    'on_e_kword_activate': lambda o: self.do_search(), \
    }
    self.cbox_backward = self.wTree.get_widget('cbox_backward')
    self.cbox_backward.set_active(self.note.note_search_backword)
    self.e_kword = self.wTree.get_widget('e_kword')
    if note.last_kword != None: self.e_kword.set_text(note.last_kword)
    note_search_history_size = get_config_key('data','note_search_history_size',  '20')
    note_search_history = get_config_key('data','note_search_history',  '')
    self.pn_completion = PnCompletion(note_search_history, '<|>' , int(note_search_history_size))
    self.e_kword.set_completion(self.pn_completion.completion)
    self.found_m1 = self.found_m2 = None
    buf = self.note.content.get_buffer()
    self.cur_iter = buf.get_iter_at_mark(buf.get_insert())
    self.wTree.signal_autoconnect(evtmap)
    
  def do_search(self):
    buf = self.note.content.get_buffer()
    self.note.last_kword = kword = self.e_kword.get_text().strip()
    try:
      if self.cbox_backward.get_active():
        self.note.note_search_backword = True
        if self.found_m1 != None:
          buf.place_cursor(buf.get_iter_at_mark(self.found_m1))
          self.cur_iter = buf.get_iter_at_mark(buf.get_insert())
        found_iter1, found_iter2 = self.cur_iter.backward_search(kword, gtk.TEXT_SEARCH_TEXT_ONLY, limit=None)
      else:
        self.note.note_search_backword = False
        if self.found_m2 != None:
          buf.place_cursor(buf.get_iter_at_mark(self.found_m2))
          self.cur_iter = buf.get_iter_at_mark(buf.get_insert())
        found_iter1, found_iter2 = self.cur_iter.forward_search(kword, gtk.TEXT_SEARCH_TEXT_ONLY, limit=None)
      self.note.content.scroll_to_iter(found_iter2, 0)
      buf.select_range(found_iter1, found_iter2)
      self.found_m1 , self.found_m2 = buf.create_mark(None, found_iter1), buf.create_mark(None, found_iter2)
      self.pn_completion.add_entry(kword)
    except: pass

class PopUpNotification():
  def __init__(self, text, callback=None):
    self.w = gtk.Window(type=gtk.WINDOW_POPUP)
    label = gtk.Label(text)
    eventbox = gtk.EventBox()
    eventbox.set_events (gtk.gdk.BUTTON_PRESS_MASK)
    eventbox.connect("button-press-event", self.do_exit)
    eventbox.add(label)
    self.w.add(eventbox)
    eventbox.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFF045") )
    gobject.timeout_add(3000, self.w.destroy)
    self.w.show_all()

  def do_exit(self):
    self.w.destroy
    if callback != None: callback()
    
  
class PnImap:
  def __init__(self, app, imapcon):
    self.app = app
    self.conn = imapcon
    self.conn.select(readonly=1)
  def is_new_mail(self):
    conn = self.conn
    retval = []
    (retcode, msgIDs) = conn.search(None, '(UNSEEN UNDELETED)') # msgIDs is like ['1 23 4 56 5']
    if retcode == 'OK':
      for msgID in msgIDs[0].split(' '):
        print 'Processing :', msgID
        try:
          (ret, mesginfo) = conn.fetch(msgID , '(BODY[HEADER.FIELDS (SUBJECT FROM)])' )
          print ret
          retval.append( (msgID, mesginfo[0][1].replace("\n\r",' ').replace("\n",' ') ) )
        except Exception, e: print "DEBUG, is_new_mail", e
    return retval


          