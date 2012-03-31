#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, re
from difflib import SequenceMatcher

class TextDiff:
     """Create diffs of text snippets."""

     def __init__(self, source, target):
         """source = source text - target = target text"""
         self.nl = u"<NL>"
         self.delTag = u"[-%s-]"
         self.insTag = u"{+%s+}"
         self.source = source.replace(u"\n", u"\n%s" % self.nl).split()
         self.target = target.replace(u"\n", u"\n%s" % self.nl).split()
         self.deleteCount, self.insertCount, self.replaceCount = 0, 0, 0
         self.diffText = None
         self.cruncher = SequenceMatcher(None, self.source,
                                         self.target)
         self._buildDiff()

     def _buildDiff(self):
         """Create a tagged diff."""
         outputList = []
         for tag, alo, ahi, blo, bhi in self.cruncher.get_opcodes():
             if tag == 'replace':
                 # Text replaced = deletion + insertion
                 outputList.append(self.delTag % u" ".join(self.source[alo:ahi]))
                 outputList.append(self.insTag % u" ".join(self.target[blo:bhi]))
                 self.replaceCount += 1
             elif tag == 'delete':
                 # Text deleted
                 outputList.append(self.delTag % u" ".join(self.source[alo:ahi]))
                 self.deleteCount += 1
             elif tag == 'insert':
                 # Text inserted
                 outputList.append(self.insTag % u" ".join(self.target[blo:bhi]))
                 self.insertCount += 1
             elif tag == 'equal':
                 # No change
                 outputList.append(u" ".join(self.source[alo:ahi]))
         diffText = u" ".join(outputList)
         #diffText = " ".join(diffText.split())
         self.diffText = diffText.replace(self.nl, u"\n")

     #def _merge(self):
	#delptn = re.compile(self.delTag.replace(u'%s', u'.+?' ), re.DOTALL )
	##insptn = re.compile(self.insTag.replace(u'%s', u'(.+?)'), re.DOTALL )
	#self.mergeText = re.sub(delptn, '', self.diffText, re.M)
	#self.mergeText = self.mergeText.replace('<i>','')
        #self.mergeText = self.mergeText.replace('</i>','')
	
     def getStats(self):
         "Return a tuple of stat values."
         return (self.insertCount, self.deleteCount, self.replaceCount)

     def getDiff(self):
         "Return the diff text."
         return self.diffText

     #def getMerge(self): self._merge(); return self.mergeText	

if __name__ == "__main__":
     try: f1,f2 = sys.argv[1], sys.argv[2]
     except: print "Usage: wdiff file1 file2"; sys.exit(1);
     ch1 = open(f1,'rb').read(); ch2 = open(f2,'rb').read()

     differ = TextDiff(ch1 , ch2)

     #print "%i insertion(s), %i deletion(s), %i replacement(s)" % differ.getStats()
     print differ.getDiff()
     #print "================"
     #print differ.getMerge()
