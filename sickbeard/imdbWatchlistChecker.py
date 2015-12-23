# Author: Frank Fenton
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of SickGear.
#
# SickGear is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickGear is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickGear.  If not, see <http://www.gnu.org/licenses/>.

import os
import traceback
import datetime

import sickbeard
from sickbeard import logger
from lib.imdb.Watchlist import WatchlistParser

class ImdbWatchlistChecker():
    def run(self, force=False):
        try:
            # add shows from trakt.tv watchlist
            if sickbeard.USE_IMDB_WATCHLIST:
                if not sickbeard.IMDB_WL_ROOT_DIR_DEFAULT and len(sickbeard.ROOT_DIRS.split('|')) < 2:
                    logger.log(u"No default root directory", logger.ERROR)
                    return
                wp = WatchlistParser()
                (updatedItems, addedItems) = wp.getShows()

        except Exception:
            logger.log(traceback.format_exc(), logger.DEBUG)
