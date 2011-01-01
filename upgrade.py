#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement 
import os,sys,sqlite3, shutil, time, random, md5

""" Run the sql script to update the database if needed between upgrade version """

from utils import *

def getNewSID2(tag=''):
        """Build a new Session ID"""
        t1 = time.time()
        t2 = t1 + random.random()
        base = md5.new( tag + str(t1 +t2) )
        sid = tag + '_' + base.hexdigest()
        return sid

def first_upgrade(con):

    cur = con.cursor()
    try: cur.execute("CREATE TABLE TEMP as select * from lsnote")
    except:
      cur.execute("DROP TABLE TEMP")
      cur.execute("CREATE TABLE TEMP as select * from lsnote")
    # this will ignore many notes with same title just copy the max id of them  
    try: 
      con.executescript("""
      DROP TABLE lsnote;
      CREATE TABLE lsnote(note_id integer primary key, title varchar(254) unique, datelog date, content text, url varchar(254), reminder_ticks unsigned long long default 0, flags varchar(50), timestamp unsigned long long, readonly integer default 0, format_tag BLOB, econtent BLOB, alert_count integer default 0, pixbuf_dict BLOB, time_spent integer default 0);
      create index reminder_ticks_idx on lsnote(reminder_ticks DESC);
      create index timestamp_idx on lsnote(timestamp DESC);""")
      csor = con.cursor()
      csor.execute("select * from TEMP")
      while (True):
        row = csor.fetchone()
        if row == None: break
        try: _time_spent = row['time_spent'] # old db may not have this field
        except: _time_spent = 0
        try:
          con.cursor().execute("INSERT INTO lsnote(note_id, title, datelog, content, url, reminder_ticks, flags, timestamp, readonly, format_tag, econtent, alert_count, pixbuf_dict, time_spent) values((?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?) ) ", (row['note_id'],row['title'], row['datelog'], row['content'], row['url'], row['reminder_ticks'], row['flags'], row['timestamp'], row['readonly'], row['format_tag'], row['econtent'], row['alert_count'], row['pixbuf_dict'], _time_spent )  )
        except Exception, e:
          print "Error, lets see what"
          if ("%s" % e).startswith('column title is not unique'):
            print "title not unique. go on to make new title if needed"
            _cs = con.cursor()
            _cs.execute("select * from lsnote where title = (?)", (row['title'],))
            _row = _cs.fetchone()
            if _row['content'] != row['content']:
              new_title = "%s - %s" % ( row['title'], getNewSID2() )
              print "okay needed and new title is %s" % new_title
              try:
                con.cursor().execute("INSERT INTO lsnote(note_id, title, datelog, content, url, reminder_ticks, flags, timestamp, readonly, format_tag, econtent, alert_count, pixbuf_dict, time_spent) values((?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?) ) ", (row['note_id'], new_title, row['datelog'], row['content'], row['url'], row['reminder_ticks'], row['flags'], row['timestamp'], row['readonly'], row['format_tag'], row['econtent'], row['alert_count'], row['pixbuf_dict'], _time_spent )  )
              except Exception, e: print "Still error? %s" % e
            _cs.close()  

      csor.close()
      con.commit()
      message_box('Success', "Operation completed succesfully. A backup file %s.backup is created. Its fate depends on you :-)" % dbpaths)
    except Exception, e:
      message_box('Error', "Sorry there is error: %s\nA backup of the database is in .backup. You can restore it in case of need." % e )
      
    cur.execute("DROP TABLE TEMP")      
  
def second_upgrade(con):
  try: con.execute("DROP TABLE deleted_notes")
  except: pass
  try:
    con.executescript(r"""
    CREATE TABLE deleted_notes(note_id int unique, timestamp integer, title varchar(254) );
    CREATE TRIGGER deleted_note AFTER DELETE ON lsnote
    BEGIN
      INSERT INTO deleted_notes(note_id, timestamp, title) values(OLD.note_id, strftime('%s','now'), OLD.title);
    END;
    CREATE TRIGGER after_insert AFTER INSERT ON lsnote
    --sqlite3 reuse ID, this avoid the non-deletable case when just new note inserted, got deleted, and inserted again then the note will be undeletable
    BEGIN
      DELETE FROM deleted_notes where note_id = NEW.note_id;
    END;
    """  )
  except: pass
      
try: dbpaths = sys.argv[1]
except:
  dbpaths = get_config_key('data', 'main_db_path', 'none')
  if dbpaths == 'none':
    chooser = gtk.FileChooserDialog(title="Select database file",action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
    dbpaths = None
    res = chooser.run()
    if res == gtk.RESPONSE_OK:
      dbpaths =  chooser.get_filename()
            
if dbpaths == 'none':
  message_box('Error', 'No database found in your pnote config. Try to setup first by running pnote.py')
  sys.exit(1)

shutil.copy( dbpaths, "%s.backup" % dbpaths )
con = sqlite3.connect(dbpaths)
con.row_factory = sqlite3.Row
con.text_factory = str
      
first_upgrade(con)
second_upgrade(con)
