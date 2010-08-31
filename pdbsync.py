#!/usr/bin/env python
# -*- coding: utf-8 -*-

import patch
import time

class DbSync:
  
  """ Take two database handle containing the lsnote table and sync them.
  * Find note_id not in each other and copy it over
  * for each note_id find title; if they are different then
    - A . Create note note with with content of B. Then
    - B Update the note to use the new  id get from A
    - B create new note with old ID and content from A
  If they are the same title
    - Take the longer content
    - check diff , compare and merger

  This will be interesting example of how to usse set :-)
  """
  def __init__(self, A, B, **args):
    A.row_factory = sqlite3.Row
    A.text_factory = str # sqlite3.OptimizedUnicode
    B.row_factory = sqlite3.Row
    B.text_factory = str # sqlite3.OptimizedUnicode
    dmp=patch.diff_match_patch()
    cursorA, cursorB = A.cursor(), B.cursor()
    base_id = args.get('base_id', 0)
    sqlcmd = 'select * from lsnote where note_id > %s' % base_id
    cursorA.execute(sqlcmd)
    cursorB.execute(sqlcmd)
    setA, setB = set(), set()
    dictA, dictB = dict(), dict()
    while (True):
      row = cursorA.fetchone()
      if (row == None): break
      setA.add(row['note_id'])
      dictA[row['note_id']] = row
    while (True):
      row = cursorB.fetchone()
      if (row == None): break
      setB.add(row['note_id'])
      dictB[row['note_id']] = row

    both_A_B_has = setA & setB
    A_not_have = setB - both_A_B_has
    B_not_have = setA - both_A_B_has

    print "A_not_have: %s records" % len(A_not_have)
    for _note_id in A_not_have:
      try:
        cursorA.execute("insert into lsnote(note_id, title, datelog, flags, content, url, readonly, timestamp, format_tag, econtent, reminder_ticks, alert_count, pixbuf_dict) values((?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?) )" , (_note_id, dictB[_note_id]['title'] , dictB[_note_id]['datelog'], dictB[_note_id]['flags'] , dictB[_note_id]['content'], dictB[_note_id]['url'], dictB[_note_id]['readonly'], dictB[_note_id]['timestamp'], dictB[_note_id]['format_tag'], dictB[_note_id]['econtent'], dictB[_note_id]['reminder_ticks'], dictB[_note_id]['alert_count'], dictB[_note_id]['pixbuf_dict']) )
      except Exception, e: print "Error: when insert to A", e

    print "B_not_have: %s records." % len(B_not_have)
    for _note_id in B_not_have:
      try:
        cursorB.execute("insert into lsnote(note_id, title, datelog, flags, content, url, readonly, timestamp, format_tag, econtent, reminder_ticks, alert_count, pixbuf_dict) values((?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?) )" , (_note_id, dictA[_note_id]['title'] , dictA[_note_id]['datelog'], dictA[_note_id]['flags'] , dictA[_note_id]['content'], dictA[_note_id]['url'], dictA[_note_id]['readonly'], dictA[_note_id]['timestamp'], dictA[_note_id]['format_tag'], dictA[_note_id]['econtent'], dictA[_note_id]['reminder_ticks'], dictA[_note_id]['alert_count'], dictA[_note_id]['pixbuf_dict']) )
      except Exception, e: print "Error: when insert to B", e

    print "Both A and B has %s records. Will sync all of them. This will take a long time!" % len(both_A_B_has)
    for _note_id in both_A_B_has:
      _A, _B = dictA[_note_id], dictB[_note_id]
      if _A['title'] == _B['title']:
        if _A['content'] == _B['content']:
          continue
        else:
            #Okay do the dirty work :-)
            _newer, _older = None, None
            if _A['timestamp'] != 0 and _B['timestamp'] != 0 and _A['timestamp'] != '' and _B['timestamp'] != '':
              if _A['timestamp'] > _B['timestamp']: _newer, _older = _A , _B
              else:  _newer, _older = _B , _A
            else:
              try:
                ticksA = time.mktime(time.strptime(_A['datelog'], "%d-%m-%Y %H:%M") )
                ticksB = time.mktime(time.strptime(_B['datelog'], "%d-%m-%Y %H:%M") )
                if ticksA > ticksB: _newer, _older = _A , _B
                else:  _newer, _older = _B , _A
              except:
                  print "All methods failed. Do teh ugliest one now. ID: {0}".format(_note_id)
                  if len(_A['content']) > len(_B['content']):
                    _newer, _older = _A , _B
                    print "A is newer"
                  else:
                    _newer, _older = _B , _A
                    print "B is newer"
            patches = dmp.patch_make(_older['content'], _newer['content'])
            _older_new_content = dmp.patch_apply( patches, _older['content'] )
            # 'sqlite3.Row' object does not support item assignment so cannot assign _A['content'] ...
            if _newer == _A: _new_contentA , _new_contentB = _A['content'], _older_new_content[0]
            else: _new_contentA , _new_contentB = _older_new_content[0], _B['content']

            try: cursorA.execute("update lsnote set title = (?), datelog = (?), flags = (?), content = (?), url = (?), readonly = (?), timestamp = (?), format_tag = (?), econtent = (?), reminder_ticks = (?), alert_count = (?), pixbuf_dict = (?) where note_id = (?)", (_A['title'], _A['datelog'], _A['flags'], _new_contentA, _A['url'], _A['readonly'], _A['timestamp'], _A['format_tag'], _A['econtent'], _A['reminder_ticks'], _A['alert_count'], _A['pixbuf_dict'], _note_id) )
            except Exception, e: print "DEBUG 0 ", e
            try: cursorB.execute("update lsnote set title = (?), datelog = (?), flags = (?), content = (?), url = (?), readonly = (?), timestamp = (?), format_tag = (?), econtent = (?), reminder_ticks = (?), alert_count = (?), pixbuf_dict = (?) where note_id = (?)", (_B['title'], _B['datelog'], _B['flags'], _new_contentB, _B['url'], _B['readonly'], _B['timestamp'], _B['format_tag'], _B['econtent'], _B['reminder_ticks'], _B['alert_count'], _B['pixbuf_dict'], _note_id) )
            except Exception, e: print "DEBUG 1 ", e
      else:
        """ Different title, they are two different notes """
        try:
          cursorA.execute("insert into lsnote(title, datelog, flags, content, url, readonly, timestamp, format_tag, econtent, reminder_ticks, alert_count, pixbuf_dict) values((?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?) )" , (dictB[_note_id]['title'] , dictB[_note_id]['datelog'], dictB[_note_id]['flags'] , dictB[_note_id]['content'], dictB[_note_id]['url'], dictB[_note_id]['readonly'], dictB[_note_id]['timestamp'], dictB[_note_id]['format_tag'], dictB[_note_id]['econtent'], dictB[_note_id]['reminder_ticks'], dictB[_note_id]['alert_count'], dictB[_note_id]['pixbuf_dict']) )
          if cursorA.lastrowid != None: _newA_id = cursorA.lastrowid
          else: print "Warning. Unable to get new id for A"
          cursorB.execute("update lsnote set note_id=(?) where note_id=(?)", (_newA_id, _note_id) )
          cursorB.execute("insert into lsnote(note_id, title, datelog, flags, content, url, readonly, timestamp, format_tag, econtent, reminder_ticks, alert_count, pixbuf_dict) values((?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?) )" , (_note_id, dictA[_note_id]['title'] , dictA[_note_id]['datelog'], dictA[_note_id]['flags'] , dictA[_note_id]['content'], dictA[_note_id]['url'], dictA[_note_id]['readonly'], dictA[_note_id]['timestamp'], dictA[_note_id]['format_tag'], dictA[_note_id]['econtent'], dictA[_note_id]['reminder_ticks'], dictA[_note_id]['alert_count'], dictA[_note_id]['pixbuf_dict']) )
        except Exception, e: print "Error: when insert to when copying from ", e

import sqlite3, MySQLdb

if  __name__ == "__main__":
  import sys,os
  con_list = []
  for dbstr in [sys.argv[1], sys.argv[2]]:
    if dbstr.startswith('mysql:'):
      (proto, host, port, dbname, user, password) = dbstr.split(':')
      connection = MySQLdb.connect(host=host, user=user,passwd = password, port = int(port) if port != '0' else 3306 )
      connection.cursor().execute('use %s' % dbname)
      con_list.append(connection)
    else:
      if os.path.isfile(dbstr):
        connection = sqlite3.connect(dbstr)
        con_list.append(connection)
      else:
        print "Error. Unrecognize resource string %s, maybe not a file of unsupported protocol" % dbstr
        print "Currently supported: sqlite3 file, mysql:host:port:dbname:username:password"
        sys.exit(1)
  try: base_id = sys.argv[3]
  except: base_id = 0
  mydbsync = DbSync(con_list[0], con_list[1], base_id = base_id)
  con_list[0].commit()
  con_list[1].commit()
  try:
    action = sys.argv[4]
    if action == 'vacuum':
      con_list[0].cursor().execute('VACUUM')
      con_list[0].cursor().execute('VACUUM')
  except: pass
