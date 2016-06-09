# -*- coding: utf-8 -*-
import sys,re
import datetime,time,sets
import unicodedata
import codecs
import MaKaC.common.info as commoninfo
import MaKaC.conference  as conference
from   MaKaC.conference    import ConferenceHolder,CategoryManager,ConferenceChair
from   MaKaC.common        import db
from   MaKaC.common.xmlGen import XMLGen
from   MaKaC.accessControl import AccessWrapper
from   MaKaC.user          import Avatar,AvatarHolder
from xml.sax.saxutils      import escape
from indico.core.db        import DBMgr

logfile = None
LOG_FILE = '/opt/indico/log/createChairFromSspeaker.log'

def log(msg):
  global logfile
  if logfile == None: logfile=open(LOG_FILE,"w")
  print msg
  logfile.write("%s\n"%msg)

# AFAIU this should be done by conf.addChair(chair)...
# But by a strange logics "Avatar" is not converted to "ConferenceChair" there,
# hence workaround...
def addChair(conf,av):
  if isinstance(av,ConferenceChair):
    newChair = av
  else:
    newChair=ConferenceChair()
    newChair.setDataFromAvatar(av)
  conf._addChair(newChair)
  """
  for c in conf.getChairList():
  print "ZZZ           %s"%(c)
  if newChair.getFirstName()  != c.getFirstName():  continue
  if newChair.getFamilyName() != c.getFamilyName(): continue
  """
  if dryRun: act = 'dryRun'
  else:      act = 'adding'
  log("%-6s     %s"%(act,{ 'id':newChair.getId(),'s':newChair.getTitle(),'fn':newChair.getFirstName(),'ln':newChair.getFamilyName(),'e':newChair.getEmail(),'affil':newChair.getAffiliation()}))

def createChair():
  global dryRun,splittedSpeaker

  dbi = DBMgr.getInstance()
  dbi.startRequest()

  for cat in CategoryManager().getList():
    for conf in cat.getConferenceList():
#     if not int(conf.getId()) in [ 3669, 3577, 1864, 5511, 5373, 5368, 5097 ]: continue
      log('--- %s %-15s %-4s %s'%(conf.getStartDate().date().isoformat(),conf.getType(),conf.getId(),conf.getTitle()))
      if conf.getType() != 'simple_event': continue

      if len(conf.getChairList()) == 0:

        sSpeakerString = conf.sspeaker.strip()
        chairs = getSimpleSpeakers(sSpeakerString,conf.sspeakerHome.strip())
        
        if len(chairs) == 0:
          if sSpeakerString: log("    ??????????????? '%s' ---> %s"%(sSpeakerString,splittedSpeaker))
        else:
          log("    >>>'%s' "%(sSpeakerString))
          for chair in chairs:  addChair(conf,chair)
          if not dryRun: dbi.commit()

      else:
        for chair in conf.getChairList():
          log("     OK %s,%s,%s"%(chair.getTitle(),chair.getFirstName(),chair.getFamilyName()))
          log("     OK %s"%(chair))
          
def parseVanVon():
  global parsedSpeaker

  """
  Alessandro D.A.M. Spallicci di Filottrano
  Astrid S. de Wijn
  Balt C. van Rees
  C. Anthony van Eysden
  Carsten van de Bruck
  Dr Astrid S. de Wijn
  Glenn van de Ven
  Jaime de la Cruz
  Jaime de la Cruz Rodrigez
  Jan Felipe Van Diejen
  Jan Pieter van der Schaar
  Jeroen van den Brink
  Luiz Garsia de Aron
  Prof. Wim J. van der Zande
  Klas Marcks von Wrtemberg
  """

  sstring = ' '.join(parsedSpeaker)

  s  =  re.search(r'(.*)( de la | van d..? )(.*)',sstring,flags=re.M|re.I)
  if not s:
    s = re.search(r'(.*)( dos | van | von | di | de | le | del )(.*)',sstring,flags=re.M|re.I)
  if s:
    parsedSpeaker = [ s.group(1).strip(), s.group(2).strip() + ' ' + s.group(3).strip() ]
    # print "parseVanVon %s --> %s" % (sstring,parsedSpeaker)
  return



def extractTitle():
  global parsedSpeaker

  title = ''
  if len(parsedSpeaker) > 0:
    ss = r'^(prof|dr|dokt|fil.doktor|ass|Astronaut|Cosmonaut|universitetslektor)\S*'
    if re.search(ss,parsedSpeaker[0],re.M|re.I):
      title = re.sub(ss,r'\1',parsedSpeaker[0],flags=re.IGNORECASE).capitalize()
      if len(title) < 5: title = title + '.'
      try:
        if re.search(r'^prof',parsedSpeaker[1],re.M|re.I):
          title = title + 'Prof.'
          del parsedSpeaker[1]
      except:
        pass
      # if parsedSpeaker[0] != title: print 'ZZZZZZZ %s -> %s' % (parsedSpeaker[0],title)
      del parsedSpeaker[0]
  return title



def getSimpleSpeakers(sSpeakerStringOrig,sSpeakerHomeString):
  global dryRun,splittedSpeaker,parsedSpeaker,organisation,matchingAvatars

  # Clean up rubbish from the "speaker" string
  sSpeakerString = re.sub(r'^--|.Cancelled.|presented .*|et al.*| OBS.*| - .*|.UNUSUAL DAY.*|Hamilton College|professor i fysik|PhD defense|will.*defend.*|.*Participants.*|.*Laureates.*|.*airline strike.*',r'',
                          re.sub(r'\(.\)|Ph. D.$|talks by ',r'',
                                 re.sub(r'  ',r' ',sSpeakerStringOrig.strip())),
                          flags=re.IGNORECASE)
  # Move title to start
  for t in [ 'professor', 'universitetslektor', 'prof.' ]:
    ul = re.search(t+'$',sSpeakerString,flags=re.IGNORECASE)
    if ul:
      sSpeakerString = t + ' ' + re.sub(t+'$','',sSpeakerString,flags=re.IGNORECASE)

  # Extract organisation (set by Sophia)
  organisation = sSpeakerHomeString
  s = re.search(r'\((.*)\)',sSpeakerString)
  if s:
    if not organisation: organisation = s.group(1)
    sSpeakerString = re.sub(r'\((.*)\)',r'',sSpeakerString).strip()
  #print "organisation: %s -> %s" % (sSpeakerHomeString,organisation)

  # continue parsing...
  dryRun = False
  chairs = []
  splittedSpeaker = re.split(r' and | och |,|&',sSpeakerString)
  for sspeaker in splittedSpeaker:
	  
    # Try to get title / firstName / lastName
    [ title,firstName,surName ] = [ '','','' ]
    parsedSpeaker = re.split(' ',sspeaker.strip())
    k = 0
    for v in parsedSpeaker:
      if not v: del parsedSpeaker[k]
      k = k + 1

    # Extract title and (if exists) remove title from the array parsedSpeaker
    title = extractTitle()

    # Parse nobless names, if any
    parseVanVon()

    # Guessing where is first/last name...
    if len(parsedSpeaker) == 0:
      break
    elif len(parsedSpeaker) == 1:
      surName = parsedSpeaker[0]
    elif len(parsedSpeaker) == 2:
      firstName = parsedSpeaker[0]
      surName = parsedSpeaker[1]
    elif len(parsedSpeaker) == 3:
      firstName = parsedSpeaker[0]
      surName = parsedSpeaker[1] + ' ' + parsedSpeaker[2]
    elif len(parsedSpeaker) == 4:
      firstName = parsedSpeaker[0]
      surName = parsedSpeaker[1] + ' ' + parsedSpeaker[2] + ' ' + parsedSpeaker[3]
 
    if not firstName and not surName:
      break

    # Serch the database by the first&last names, may be the person is known
    matchingAvatars = AvatarHolder().match({'surName':surName,"name":firstName}, exact=1)
    nothingFound = (len(matchingAvatars) == 0)

    # Create an avatar if it was found in the database
    if nothingFound: 
      createAvatar(title,firstName,surName)

    # I am not (yet) sure how ah.match works, lets better check twice the result... 
    notConfirmed = True
    for av in matchingAvatars:
      if (surName.lower()   == av.getSurName().lower() and 
          firstName.lower() == av.getName().lower()):  
        notConfirmed = False
        #if (len(matchingAvatars)==1 and len(splittedSpeaker) == 1): dryRun = False
        chairs.append(av)
        if not nothingFound: print "ZZZZ accepted... %s"%av 
        break # Stop after the first match :-)
    if (not nothingFound and notConfirmed) or not chairs:
      av = createAvatar(title,firstName,surName)
      if not av is None: chairs.append(av)

  return list(set(chairs))

def createAvatar(title,firstName,surName):
  global matchingAvatars

  e = []  
  if firstName: e.append(firstName)
  if surName:   e.append(surName)
  if not e: return None

  email = re.sub(' ','.',('.'.join(e)+'@somewhere.earth').decode('utf-8').encode("ascii","ignore"))
  av = Avatar({ 'email':   email,
                'name' :   firstName,
                'surName': surName,
                'title': title,
                'organisation':[organisation] })
  matchingAvatars.append(av)
  print "ZZZZ created %s %s" % (av.getFirstName(),av.getFamilyName())
  return av

      
if __name__ == '__main__':
  
    createChair()

