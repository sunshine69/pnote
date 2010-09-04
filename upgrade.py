#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os,sys,sqlite3, shutil, time

""" Run the sql script to update the database if needed between upgrade version """

from utils import *
dbpaths = get_config_key('data', 'main_db_path', 'none')
if dbpaths == 'none':
  message_box('Error', 'No database found in your pnote config. Try to setup first by running pnote.py')
  sys.exit(1)
  
shutil.copy( dbpaths, "%s.backup" % dbpaths )
con = sqlite3.connect(dbpaths)
con.row_factory = sqlite3.Row
con.text_factory = str

def first_upgrade(con):

    cur = con.cursor()
    try: cur.execute("CREATE TABLE TEMP as select * from lsnote")
    except:
      cur.execute("DROP TABLE TEMP")
      cur.execute("CREATE TABLE TEMP as select * from lsnote")
    try: 
      con.executescript("""
      DROP TABLE lsnote;
      CREATE TABLE lsnote(note_id integer primary key, title varchar(254) unique, datelog date, content text, url varchar(254), reminder_ticks unsigned long long default 0, flags varchar(50), timestamp unsigned long long, readonly integer default 0, format_tag BLOB, econtent BLOB, alert_count integer default 0, pixbuf_dict BLOB);
      create index reminder_ticks_idx on lsnote(reminder_ticks DESC);
      create index timestamp_idx on lsnote(timestamp DESC);
      INSERT INTO lsnote(note_id, title, datelog, content, url, reminder_ticks, flags, timestamp, readonly, format_tag, econtent,alert_count, pixbuf_dict) select min(note_id) as note_id, title, datelog, content, url, reminder_ticks, flags, timestamp, readonly, format_tag, econtent,alert_count, pixbuf_dict  from TEMP group by title;
      DROP TABLE TEMP;
      VACUUM;
      """)
      con.commit()
      message_box('Success', "Operation completed succesfully. A backup file %s.backup is created. Its fate depends on you :-)" % dbpaths)
    except Exception, e:
      cur.execute("DROP TABLE TEMP")
      message_box('Error', "Sorry there is error: %s\nA backup of the database is in %s.backup. You can restore it in case of need." % e)
  
def second_upgrade(con):
  try: con.execute("DROP TABLE deleted_notes")
  except: pass
  try:
    con.executescript(r"""
    CREATE TABLE deleted_notes(note_id int unique, timestamp integer );
    CREATE TRIGGER deleted_note AFTER DELETE ON lsnote
    BEGIN
      INSERT INTO deleted_notes(note_id, timestamp) values(OLD.note_id, strftime('%s','now'));
    END;
    """  )
  except: pass
      
first_upgrade(con)
second_upgrade(con)