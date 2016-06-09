# -*- coding: utf-8 -*-
##
##
## This file is part of Indico.
## Copyright (C) 2002 - 2014 European Organization for Nuclear Research (CERN).
##
## Indico is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 3 of the
## License, or (at your option) any later version.
##
## Indico is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Indico;if not, see <http://www.gnu.org/licenses/>.

import sys


from indico.core.db import DBMgr
from MaKaC.conference import CategoryManager
from MaKaC.common import indexes
import transaction

def main():
    """This script deletes existing category indexes and recreates them."""
    DBMgr.getInstance().startRequest()
    im = indexes.IndexesHolder()
    im.removeById('category')
    catIdx = im.getIndex('category')
    ch = CategoryManager()
    print "\n%s categories to be processed" % len(ch.getList())
    totcats = 0
    totconfs = 0
    for cat in ch.getList():
        totcats = totcats + 1
        try:    conferences = cat.conferences.values()
        except: conferences = cat.getConferenceList()
        print "\n%s (%s conferences)" % (cat.getTitle(),len(conferences))
        while 1:
            try:
                for conf in conferences:
                    totconfs = totconfs + 1
                    print "   %4s %s" % (conf.getId(),conf.getTitle())
                    catIdx.indexConf(conf)
                transaction.commit()
                break
            except:
                DBMgr.getInstance().sync()
    DBMgr.getInstance().endRequest()

    print "\nDONE, %s categories, %s conferences\n" % (totcats,totconfs)

if __name__ == "__main__":
    main()

