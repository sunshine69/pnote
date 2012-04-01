#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement
import time
import sqlite3, random, re
import shlex, subprocess, os, codecs

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
  wierd problem there some IDs that just swapping around but seems no problempn
  the problem is that sync with another note which have duplicate title. Need to write something to normalize these
  """
  def __init__(self, A, B, **args):
    A.row_factory = sqlite3.Row
    A.text_factory = str # sqlite3.OptimizedUnicode
    B.row_factory = sqlite3.Row
    B.text_factory = str # sqlite3.OptimizedUnicode
    self.A = A; self.B = B; self.args = args
    self.DEBUG = args.get('DEBUG', False)
    self.return_msg = ''
    self.last_sync_id = 0

  def merge_two_text(self, text1, text2):
          #codecs.open("/tmp/_pnote_temp_text1", "wb").write(text1)
          #codecs.open("/tmp/_pnote_temp_text2", "wb").write(text2)
          #cmd = "cdiff -merge3 /tmp/_pnote_temp_text1 /tmp/_pnote_temp_text2"
          #(stdoutdata, stderrdata) = subprocess.Popen(shlex.split(cmd), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
          #os.unlink("/tmp/_pnote_temp_text1"); os.unlink("/tmp/_pnote_temp_text2")
          from wdiff import TextDiff
          differ = TextDiff(text1 , text2)
          output = differ.getDiff()
          if re.search('[a-zA-Z]',output): return output
          else:
                  msg = "merge_two_text: Warning. Empty output. Will return the one bigger"
                  if self.DEBUG: print "%s\nInput text1 is: \n%s\ntext2 is: \n%s\n" % (msg, text1, text2)
                  self.return_msg += "\n%s" % (msg)
                  output = (text1 if len(text1) > len(text2) else text2)
                  print "return_msg: '%s'\ntext1: '%s'\ntext2: '%s'" % (output, text1, text2)
                  return output

  def normalize_title(self, A):
    # A has many notes same title, Added to B with title changes
    cursorA = A.cursor()
    cursorA.execute("select * from lsnote")
    title_dict = dict()
    while (True):
            row = cursorA.fetchone()
            if row == None: break
            if row['title'] not in title_dict:
                    title_dict[row['title']] = {'note_id': row['note_id'], 'datelog': row['datelog'], 'flags': row['flags'], 'content': row['content'], 'url': row['url'], 'readonly': row['readonly'], 'timestamp': row['timestamp'], 'format_tag': row['format_tag'], 'econtent': row['econtent'], 'reminder_ticks': row['reminder_ticks'], 'alert_count': row['alert_count'], 'pixbuf_dict': row['pixbuf_dict'] }
            else:
                    print "Need to merge/new title: title: '%s'" % row['title']
                    if row['datelog'] == title_dict[row['title']]['datelog']:
                            print "mergee using cdiff.."
                            title_dict[row['title']]['content'] = self.merge_two_text(title_dict[row['title']]['content'], row['content'] )
                    else:
                        new_title = "%s - %s_%s" % (row['title'] , 'new_title' , str(random.randint(0,100000) ))
                        print "Creating new title %s" % new_title
                        title_dict[new_title] = {'note_id': row['note_id'], 'datelog': row['datelog'], 'flags': row['flags'], 'content': row['content'], 'url': row['url'], 'readonly': row['readonly'], 'timestamp': row['timestamp'], 'format_tag': row['format_tag'], 'econtent': row['econtent'], 'reminder_ticks': row['reminder_ticks'], 'alert_count': row['alert_count'], 'pixbuf_dict': row['pixbuf_dict'] }

    cursorA.execute("delete from lsnote")
    for key in dict.keys(title_dict):
            cursorA.execute("insert into lsnote(note_id, title, datelog, flags, content, url, readonly, timestamp, format_tag, econtent, reminder_ticks, alert_count, pixbuf_dict) values((?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?) )" , (title_dict[key]['note_id'], key, title_dict[key]['datelog'], title_dict[key]['flags'], title_dict[key]['content'], title_dict[key]['url'], title_dict[key]['readonly'], title_dict[key]['timestamp'], title_dict[key]['format_tag'], title_dict[key]['econtent'] , title_dict[key]['reminder_ticks'], title_dict[key]['alert_count'], title_dict[key]['pixbuf_dict']) )
    A.commit()
    # No not doing it

  def do_sync(self):
    A = self.A; B = self.B
    cursorA, cursorB = A.cursor(), B.cursor()
    timestamp = self.args.get('timestamp', 0)
    if timestamp == 0:
        base_id = self.args.get('base_id', 0)
        self.return_msg += 'No timestamp supplied. use base_id %s' % base_id
        sqlcmd = 'select * from lsnote where note_id >= %s' % base_id
    else:
        self.return_msg += 'Sync from \'%s\'' % time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(timestamp))
        sqlcmd = 'select * from lsnote where timestamp >= %s' % timestamp

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

    msg = "\nA_not_have: %s records" % len(A_not_have)
    self.return_msg += msg
    if self.DEBUG:
      print msg
      print A_not_have
    for _note_id in A_not_have:
      try:
        try:
                cursorA.execute("select * from deleted_notes where note_id = %s" % _note_id )
                ret_val = cursorA.fetchone()
                if ret_val != None:
                        if ret_val['timestamp'] >= dictB[_note_id]['timestamp'] and ret_val['title'] == dictB[_note_id]['title']:
                                try: cursorB.execute("delete from lsnote where note_id = %s" % (_note_id) )
                                except: pass
                                try: cursorB.execute("delete from deleted_notes where note_id = %s" % (_note_id) )
                                except: pass
                                try: cursorA.execute("delete from deleted_notes where note_id = %s" % (_note_id) )
                                except: pass
                                continue
        except Exception, e: print "Error: %s (ignored)" % e
        if self.DEBUG: print "gone to insert id: %s, title: %s"   % (_note_id, dictB[_note_id]['title'])
        cursorA.execute("insert into lsnote(note_id, title, datelog, flags, content, url, readonly, timestamp, format_tag, econtent, reminder_ticks, alert_count, pixbuf_dict) values((?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?) )" , (_note_id, dictB[_note_id]['title'] , dictB[_note_id]['datelog'], dictB[_note_id]['flags'] , dictB[_note_id]['content'], dictB[_note_id]['url'], dictB[_note_id]['readonly'], dictB[_note_id]['timestamp'], dictB[_note_id]['format_tag'], dictB[_note_id]['econtent'], dictB[_note_id]['reminder_ticks'], dictB[_note_id]['alert_count'], dictB[_note_id]['pixbuf_dict']) )
        print "Insert to A OK: id: %s, title: %s" % (_note_id, dictB[_note_id]['title'])
      except Exception, e:
        print "Colision detected. Trying to resolve .."
        if ("%s" % e).startswith('column title is not unique'):
          print "because of same title"
          cursorA.execute("select count(*) as rcount from lsnote where title = (?)", (dictB[_note_id]['title'],))
          if cursorA.fetchone()['rcount'] > 1: print "Database A need to run normalize_title. Aborting ."; sys.exit(1)
          try:
              cursorA.execute("select *  from lsnote where title = (?)", (dictB[_note_id]['title'],))
              r = cursorA.fetchone()
              new_content = self.merge_two_text(r['content'], dictB[_note_id]['content'] )
              cursorA.execute("update lsnote set note_id = (?), content = (?) where title = (?)" , (_note_id, new_content, dictB[_note_id]['title'] ) )
              cursorB.execute("update lsnote set note_id = (?), content = (?) where title = (?)" , (_note_id, new_content, dictB[_note_id]['title'] ) )

          except Exception, e:
            print "Error updating A: %s" % e
            print "Error: when insert to A", e
            self.return_msg += "\nERROR when insert to A: %s: Title: %s" % ( e, dictB[_note_id]['title'])
        else:
            print "Error %s" % e
            # one has updated a note and the other not having it updated recently. Thus in first select the id not appear but in fact it has. Update it
            if ("%s" % e).startswith('PRIMARY KEY must be unique'):
                cursorA.execute("select * from lsnote where note_id = %s " % _note_id )
                r = cursorA.fetchone()
                if r['title'] == dictB[_note_id]['title']:
                    new_content = self.merge_two_text(r['content'],dictB[_note_id]['content'] )
                    try: cursorA.execute("update lsnote set title = (?), datelog = (?), flags = (?), content = (?), url = (?), readonly = (?), timestamp = (?), format_tag = (?), econtent = (?), reminder_ticks = (?), alert_count = (?), pixbuf_dict = (?) where note_id = (?)", (dictB[_note_id]['title'], dictB[_note_id]['datelog'], dictB[_note_id]['flags'], new_content, dictB[_note_id]['url'], dictB[_note_id]['readonly'], dictB[_note_id]['timestamp'], dictB[_note_id]['format_tag'], dictB[_note_id]['econtent'], dictB[_note_id]['reminder_ticks'], dictB[_note_id]['alert_count'], dictB[_note_id]['pixbuf_dict'], _note_id) )
                    except Exception, e: print "Error: %s" % e
      #self.A.commit()
    msg = "\nB_not_have: %s records." % len(B_not_have)
    self.return_msg += msg
    if self.DEBUG:
      print msg
      print B_not_have
    for _note_id in B_not_have:
      try:
        try:
                cursorB.execute("select * from deleted_notes where note_id = %s" % _note_id )
                ret_val = cursorB.fetchone()
                if ret_val != None:
                        if ret_val['timestamp'] >= dictA[_note_id]['timestamp'] and ret_val['title'] == dictA[_note_id]['title']:
                                try: cursorA.execute("delete from lsnote where note_id = %s" % (_note_id) )
                                except: pass
                                try: cursorA.execute("delete from deleted_notes where note_id = %s" % (_note_id) )
                                except: pass
                                try: cursorB.execute("delete from deleted_notes where note_id = %s" % (_note_id) )
                                except: pass
                                continue
        except Exception, e: print "Error: %s, ignored" % e
        if self.DEBUG: print "gone to insert id: %s, title: %s"   % (_note_id, dictA[_note_id]['title'])
        cursorB.execute("insert into lsnote(note_id, title, datelog, flags, content, url, readonly, timestamp, format_tag, econtent, reminder_ticks, alert_count, pixbuf_dict) values((?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?) )" , (_note_id, dictA[_note_id]['title'] , dictA[_note_id]['datelog'], dictA[_note_id]['flags'] , dictA[_note_id]['content'], dictA[_note_id]['url'], dictA[_note_id]['readonly'], dictA[_note_id]['timestamp'], dictA[_note_id]['format_tag'], dictA[_note_id]['econtent'], dictA[_note_id]['reminder_ticks'], dictA[_note_id]['alert_count'], dictA[_note_id]['pixbuf_dict']) )
        print "Insert to B OK: id: %s, title: %s" % (_note_id, dictA[_note_id]['title'])
      except Exception, e:
        print "Colision detected. Trying to resolve .."
        if ("%s" % e).startswith('column title is not unique'):
            cursorB.execute("select count(*) as rcount from lsnote where title = (?)", (dictA[_note_id]['title'],))
            if cursorB.fetchone()['rcount'] > 1: print "Database B need to run normalize_title. Aborting ."; sys.exit(1)
            try:
                cursorB.execute("select *  from lsnote where title = (?)", (dictA[_note_id]['title'],))
                r = cursorB.fetchone()
                new_content = self.merge_two_text(r['content'], dictA[_note_id]['content'] )
                cursorB.execute("update lsnote set note_id = (?), content = (?) where title = (?)" , (_note_id, new_content, dictA[_note_id]['title'] ) )
                cursorA.execute("update lsnote set note_id = (?), content = (?) where title = (?)" , (_note_id, new_content, dictA[_note_id]['title'] ) )

            except Exception, e:
                if self.DEBUG:
                    print "Error updating B: %s" % e
                    print "Error: when insert to B %s" % e
                self.return_msg += "\nERROR when insert to B: %s: Title: %s" % (e, dictA[_note_id]['title'])
        else:
            print "Error %s" % e
            if ("%s" % e).startswith('PRIMARY KEY must be unique'):
                cursorB.execute("select * from lsnote where note_id = %s " % _note_id )
                r = cursorB.fetchone()
                if r['title'] == dictA[_note_id]['title']:
                    new_content = self.merge_two_text(r['content'],dictA[_note_id]['content'] )
                    try: cursorB.execute("update lsnote set title = (?), datelog = (?), flags = (?), content = (?), url = (?), readonly = (?), timestamp = (?), format_tag = (?), econtent = (?), reminder_ticks = (?), alert_count = (?), pixbuf_dict = (?) where note_id = (?)", (dictA[_note_id]['title'], dictA[_note_id]['datelog'], dictA[_note_id]['flags'], new_content, dictA[_note_id]['url'], dictA[_note_id]['readonly'], dictA[_note_id]['timestamp'], dictA[_note_id]['format_tag'], dictA[_note_id]['econtent'], dictA[_note_id]['reminder_ticks'], dictA[_note_id]['alert_count'], dictA[_note_id]['pixbuf_dict'], _note_id) )
                    except Exception, e: print "Error: %s" % e

      #self.B.commit()
    msg =  "\nBoth A and B has %s records. Will sync all of them. This will take a long time!" % len(both_A_B_has)
    self.return_msg += msg
    if self.DEBUG: print msg
    cursorA.execute("select max(note_id) as last_sync_id from lsnote")
    self.last_sync_id = cursorA.fetchone()['last_sync_id']

    if self.args.get('skip_patch'):
      if self.DEBUG: print "skip_patch is true, skiping"
      return self.commit()

    for _note_id in both_A_B_has:
      _A, _B = dictA[_note_id], dictB[_note_id]
      if _A['title'] == _B['title']:
        if _A['content'] == _B['content'] and _A['readonly'] == _B['readonly'] and _A['url'] == _B['url'] and _A['flags'] == _B['flags'] and _A['econtent'] == _B['econtent']:
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
                  if self.DEBUG: print "All methods failed. Do the ugliest one
                  now. ID: %s" % _note_id
                  if len(_A['content']) > len(_B['content']):
                    _newer, _older = _A , _B
                    if self.DEBUG: print "A is newer"
                  else:
                    _newer, _older = _B , _A
                    if self.DEBUG: print "B is newer"
            if _A['content'] != _B['content']:
                _merge_content = self.merge_two_text(_older['content'], _newer['content'])
                # 'sqlite3.Row' object does not support item assignment so cannot assign _A['content'] ...
                _new_contentA = _new_contentB =  _merge_content
            else: _new_contentA = _new_contentB = _A['content']
            try: cursorA.execute("update lsnote set title = (?), datelog = (?), flags = (?), content = (?), url = (?), readonly = (?), timestamp = (?), format_tag = (?), econtent = (?), reminder_ticks = (?), alert_count = (?), pixbuf_dict = (?) where note_id = (?)", (_A['title'], _A['datelog'], _A['flags'], _new_contentA, _A['url'], _A['readonly'], _A['timestamp'], _A['format_tag'], _A['econtent'], _A['reminder_ticks'], _A['alert_count'], _A['pixbuf_dict'], _note_id) )
            except Exception, e:
              if self.DEBUG: print "DEBUG 0 ", e
              self.return_msg += "\nDEBUG0 error"
            try: cursorB.execute("update lsnote set title = (?), datelog = (?), flags = (?), content = (?), url = (?), readonly = (?), timestamp = (?), format_tag = (?), econtent = (?), reminder_ticks = (?), alert_count = (?), pixbuf_dict = (?) where note_id = (?)", (_B['title'], _B['datelog'], _B['flags'], _new_contentB, _B['url'], _B['readonly'], _B['timestamp'], _B['format_tag'], _B['econtent'], _B['reminder_ticks'], _B['alert_count'], _B['pixbuf_dict'], _note_id) )
            except Exception, e:
              if self.DEBUG: print "DEBUG 1 ", e
              self.return_msg += "\nDEBUG1 error: %s" % e
      else:
        """ Different title, they are two different notes """

        try:
          cursorA.execute("insert into lsnote(title, datelog, flags, content, url, readonly, timestamp, format_tag, econtent, reminder_ticks, alert_count, pixbuf_dict) values((?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?) )" , (dictB[_note_id]['title'] , dictB[_note_id]['datelog'], dictB[_note_id]['flags'] , dictB[_note_id]['content'], dictB[_note_id]['url'], dictB[_note_id]['readonly'], dictB[_note_id]['timestamp'], dictB[_note_id]['format_tag'], dictB[_note_id]['econtent'], dictB[_note_id]['reminder_ticks'], dictB[_note_id]['alert_count'], dictB[_note_id]['pixbuf_dict']) )
          if cursorA.lastrowid != None:
            _newA_id = cursorA.lastrowid
            cursorB.execute("update lsnote set note_id=(?) where note_id=(?)", (_newA_id, _note_id) )
          else:
            if self.DEBUG: print "Warning. Unable to get new id for A"

        except Exception, e:
            if ("%s" % e).startswith('column title is not unique'):
              # If A has a ntoe with the same title of the B then inserting here will conflict. Actually they both have same note but different ID. Daling with by update A this title to hieash one, and then B the same ID (w created a hole in ID but it is fine)
              next_id = self.last_sync_id + 1
              # Hope that only one note has same title. We did remove duplicate using upgrade.py script anyway. If not the case, run that script again to normalize data
              try:
                cursorA.execute("UPDATE lsnote set note_id = (?) where title = (?)", (next_id, _B['title'] ) )
                cursorB.execute("UPDATE lsnote set note_id = (?) where title = (?)", (next_id, _B['title']) )
                self.last_sync_id = next_id
              except Exception, e:
                if self.DEBUG:  print "Error DEBUG2: %s" % e
            else:
              if self.DEBUG: print "Error: when insert to A / copying from B: %s " % e
              self.return_msg += "\nError: when insert to when copying from: %s: Title A: %s, B: %s" % (e , _A['title'], _B['title'])
        try:
          cursorB.execute("insert into lsnote(note_id, title, datelog, flags, content, url, readonly, timestamp, format_tag, econtent, reminder_ticks, alert_count, pixbuf_dict) values((?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?), (?) )" , (_note_id, dictA[_note_id]['title'] , dictA[_note_id]['datelog'], dictA[_note_id]['flags'] , dictA[_note_id]['content'], dictA[_note_id]['url'], dictA[_note_id]['readonly'], dictA[_note_id]['timestamp'], dictA[_note_id]['format_tag'], dictA[_note_id]['econtent'], dictA[_note_id]['reminder_ticks'], dictA[_note_id]['alert_count'], dictA[_note_id]['pixbuf_dict']) )
        except Exception, e:
          if ("%s" % e).startswith('column title is not unique'):
            next_id = self.last_sync_id + 1
            # Hope that only one note has same title. We did remove duplicate using upgrade.py script anyway. If not the case, run that script again to normalize data
            try:
              cursorB.execute("UPDATE lsnote set note_id = (?) where title = (?)", (next_id, _A['title'] ) )
              cursorA.execute("UPDATE lsnote set note_id = (?) where title = (?)", (next_id, _A['title']) )
              self.last_sync_id = next_id
            except Exception, e: print "Error DEBUG3: %s" % e
          else:
              if self.DEBUG: print "Error: when insert to B / copying from A: %s " % e
              self.return_msg += "\nError: when insert to when copying from: %s: Title A: %s, B: %s" % (e , _A['title'], _B['title'])

    return self.commit()

  def commit(self):
    print "going to commit changes..."
    self.A.commit()
    self.B.commit()
    msg = "\nOperation completed successfully"
    self.return_msg += msg
    print msg
    return self


if  __name__ == "__main__":
  import sys,os
  con_list = []
  for dbstr in [sys.argv[1], sys.argv[2]]:
    if dbstr.startswith('mysql:'):
      import MySQLdb
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
  mydbsync = DbSync(con_list[0], con_list[1], base_id = base_id, skip_patch = False, DEBUG = True)
  #mydbsync.normalize_title(con_list[0])
  mydbsync.normalize_title(con_list[1])
  mydbsync.do_sync()
  #mydbsync.commit()
  print "=================="
  print mydbsync.return_msg
  try:
    action = sys.argv[4]
    if action == 'vacuum':
      con_list[0].cursor().execute('VACUUM')
      con_list[0].cursor().execute('VACUUM')
  except: pass
