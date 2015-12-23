#Author: P0psicles
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

import re
import requests
import sickbeard
from sickbeard import helpers, logger, db
from sickbeard import encodingKludge as ek
import os
import traceback
import datetime
import json
from lib.imdb._exceptions import IMDbError
from lib.libtrakt import TraktAPI
from lib.libtrakt.exceptions import traktException
'''
'''
class WatchlistItem():
    def __init__(self,imdbid,indexer=1,indexer_id=None,watchlist_id=None,show_id=None,score=None,title=None):
        self.imdbid = imdbid
        self.indexer = indexer
        self.indexer_id = indexer_id
        self.watchlist_id = watchlist_id
        self.show_id = show_id
        self.score = score
        self.title = title
        
    def addDefaults(self):
        """
        Adds a new show with the default settings
        """
        if not helpers.findCertainShow(sickbeard.showList, int(self.indexer_id)):
            logger.log(u"Adding show " + str(self.indexer_id))
            root_dirs = sickbeard.ROOT_DIRS.split('|')

            try:
                root_dir_index = sickbeard.IMDB_WL_ROOT_DIR_DEFAULT -1 if sickbeard.IMDB_WL_USE_CUSTOM_DEFAULTS and sickbeard.IMDB_WL_ROOT_DIR_DEFAULT else 0
                location = root_dirs[int(root_dirs[root_dir_index]) + 1]
            except:
                location = None

            if location:
                showPath = ek.ek(os.path.join, location, helpers.sanitizeFileName(self.title))
                dir_exists = helpers.makeDir(showPath)
                if not dir_exists:
                    logger.log(u"Unable to create the folder " + showPath + ", can't add the show", logger.ERROR)
                    return
                else:
                    helpers.chmodAsParent(showPath)
                
                # Set defaults
                quality = int(sickbeard.QUALITY_DEFAULT)
                status = int(sickbeard.STATUS_DEFAULT)
                wanted_begin = int(sickbeard.WANTED_BEGIN_DEFAULT)
                wanted_latest = int(sickbeard.WANTED_LATEST_DEFAULT)
                flatten_folders = int(sickbeard.FLATTEN_FOLDERS_DEFAULT)
                subtitles = int(sickbeard.SUBTITLES_DEFAULT)
                anime = int(sickbeard.ANIME_DEFAULT)
                indexer = sickbeard.INDEXER_DEFAULT
                
                if sickbeard.IMDB_WL_USE_CUSTOM_DEFAULTS:
                    quality = int(sickbeard.IMDB_WL_QUALITY_DEFAULT)
                    status = int(sickbeard.IMDB_WL_STATUS_DEFAULT)
                    wanted_begin = int(sickbeard.IMDB_WL_WANTED_BEGIN_DEFAULT)
                    wanted_latest = int(sickbeard.IMDB_WL_WANTED_LATEST_DEFAULT)
                    flatten_folders = int(sickbeard.IMDB_WL_FLATTEN_FOLDERS_DEFAULT)
                    subtitles = int(sickbeard.IMDB_WL_SUBTITLES_DEFAULT)
                    indexer = int(sickbeard.IMDB_WL_INDEXER_DEFAULT)
                    #IMDB_WL_INDEXER_TIMEOUT = Nonef
                    #IMDB_WL_SCENE_DEFAULT = False
                    anime = sickbeard.IMDB_WL_ANIME_DEFAULT
                    #IMDB_WL_USE_IMDB_INFO = True

                
                sickbeard.showQueueScheduler.action.addShow(int(indexer), int(self.indexer_id), showPath, status,
                                                            quality, flatten_folders, wanted_begin=wanted_begin, 
                                                            wanted_latest=wanted_latest, 
                                                            subtitles=subtitles, anime=anime)
            else:
                logger.log(u"There was an error creating the show, no root directory setting found", logger.ERROR)
                return
            
    def getIdFromTrakt(self):
        try:
            search_id = re.search(r'(?m)((?:tt\d{4,})|^\d{4,}$)', self.imdbid).group(1)
            
            url = '/search?id_type=%s&id=%s' % (('tvdb', 'imdb')['tt' in search_id], search_id)
            filtered = []
            try:
                resp = TraktAPI(ssl_verify=sickbeard.TRAKT_VERIFY, timeout=sickbeard.TRAKT_TIMEOUT).trakt_request(url)
                if len(resp):
                    filtered = resp
            except traktException as e:
                logger.log(u'Could not connect to Trakt service: %s' % ex(e), logger.WARNING)
            
            # Use first returend show. Sometimes a single IMDB id can have multiple tvdb id's. Like for example with Star trek: renagades
            for result in resp:
                if result['type'] == "show":
                    self.title = result['show']['title']
                    self.indexer_id = result['show']['ids']['tvdb']
                    # As where default setting the tvdb indexer_id, might as well keep it static for now.
                    self.indexer = 1
                    return True

        except Exception, e:
            logger.log(u"Could not get TVDBid from Trakt using id_type imdb", logger.WARNING)
            return False
    
    def updateDb(self):
        # Check if the show already exists else insert it into the table
        insert_wl_item = None
        myDB = db.DBConnection()
        if not myDB.select(
            'SELECT imdb_id FROM imdb_watchlist WHERE imdb_id = ?', [self.imdbid]):
            insert_wl_item = myDB.action('INSERT INTO imdb_watchlist (imdb_id, indexer, indexer_id, watchlist_id, show_id, last_added) VALUES (?,?,?,?,?,?)',
                     [self.imdbid, self.indexer, self.indexer_id, self.watchlist_id, self.show_id, datetime.datetime.now()])
        return insert_wl_item
    
class IMDBWatchlistApi(object):
    def __init__(self, timeout=None):
        self.session = requests.Session()
        #self.verify = ssl_verify and sickbeard.TRAKT_VERIFY and certifi.where()
        self.timeout = timeout or sickbeard.IMDB_WL_TIMEOUT
        self.headers = {
            'Content-Type': 'application/json',
        }
        self.WATCHLIST_URL = u"http://www.imdb.com/list/_ajax/list_filter?"
        
    def watchlist_request(self, data=None, headers=None, url=None, method='GET', count=0, conttype='application/json', params=None):
        if not url:
            url = self.WATCHLIST_URL
        
        try:
            resp = self.session.request(method, url, headers=self.headers, timeout=self.timeout,
                                        params=params if params else [], verify=False)
            
            # check for http errors and raise if any are present
            resp.raise_for_status()
            
            if conttype == 'application/json':
                resp = resp.json()
        except requests.RequestException as e:
            code = getattr(e.response, 'status_code', None)
            if not code:
                if 'timed out' in e:
                    logger.log(u'Timeout connecting to Trakt. Try to increase timeout value in Trakt settings', logger.WARNING)                      
                # This is pretty much a fatal error if there is no status_code
                # It means there basically was no response at all                    
                else:
                    logger.log(u'Could not connect to Trakt. Error: {0}'.format(e), logger.WARNING)                
            elif 502 == code:
                # Retry the request, Cloudflare had a proxying issue
                logger.log(u'Retrying api request url: %s' % url, logger.WARNING)
                return self.trakt_request(data, headers, url, method, count=count)
            elif code in (500, 501, 503, 504, 520, 521, 522):
                # http://docs.trakt.apiary.io/#introduction/status-codes
                logger.log(u'Trakt may have some issues and it\'s unavailable. Try again later please', logger.WARNING)
            elif 404 == code:
                logger.log(u'Trakt error (404) the resource does not exist: %s' % url, logger.WARNING)
            else:
                logger.log(u'Could not connect to Trakt. Code error: {0}'.format(code), logger.ERROR)
            return {}
        
        # check and confirm Trakt call did not fail
        if isinstance(resp, dict) and 'failure' == resp.get('status', None):
            if 'message' in resp:
                raise IMDbError(resp['message'])
            if 'error' in resp:
                raise IMDbError(resp['error'])
            else:
                raise IMDbError('Unknown Error')

        return resp

class WatchlistParser(IMDBWatchlistApi):
    def __init__(self):
        super(WatchlistParser, self).__init__()
        self.watchlist_items = []
    
    #Helper
    def parse(self, html):
        nrAddedTTs = 0
        ### Get the tt's (shows) from the ajax html. E.a. [ tt1958961|imdb|8.1|8.1|list, tt1958961|imdb|8.1|8.1|list ]
        if not html or not html.has_key('table_data') or not int(html['num_results']):
            return False
        
        shows = re.findall("(tt[0-9]+)\\|imdb\\|([.0-9]+)", html['table_data'])
        if shows:
            return shows
        
        return False
    
    def getShows(self):
        
        shows = []
        
        ### Get the configured imdb watchlist urls
        watchlists = sickbeard.IMDB_WL_USE_IDS.split('|')
        
        ### We're only intrested in enabled watchlists
        watchlists_enabled = sickbeard.IMDB_WL_IDS_ENABLED.split('|')
        
        if len(watchlists) == len(watchlists_enabled):
            # Start looping through the imdb watchlist urls
            for index, watchlist in enumerate(watchlists):
                if not int(watchlists_enabled[index]):
                    continue
                
                # Get the query data used for constructing the watchlist ajax url
                query_data = self.convertUrlData(watchlist)
                
                # Perform the ajax request for the watchlist
                html = self.watchlist_request(params=query_data)
                
                #Extract all imdb_id's
                shows = self.parse(html)
                
                # Move through the imdb_ids and create WatchlistItem objects for them
                # Don't konw why i'm keeping the scores. Maybe comes of use some day.
                for show in shows:
                    if show[0] not in [x.imdbid for x in self.watchlist_items]:
                        self.watchlist_items.append(WatchlistItem(show[0],score=show[1],watchlist_id=index))
        
        updatedItems = addedItems = []
        for item in self.watchlist_items:
            if not item.getIdFromTrakt():
                logger.log("Could not enrich, adding to db without indexer_id", logger.WARNING)
            else:
                item.addDefaults()
            # Insert the swhow into the imdb_watchlist table if not already exists
            # Return True if inserted, False of already exists
            if item.updateDb():
                addedItems.append(item)

        return (updatedItems, addedItems)
    
    '''
    Tries to use the csvUrls as a comma separated list of imdb csv urls, 
    to retrieve a userid and listid for each of the csv url.
    For each csv url an Ajax url is created. Thats used to get the list of Tvshows.
    '''
    def convertUrlData(self, watchlist_url):
        ajaxUrls = []
        ajaxUrlBase = u"http://www.imdb.com/list/_ajax/list_filter?"
        
        reUserId = re.compile(".*(ur[0-9]+)")
        reListId = re.compile(".*(ls[0-9]+)")
        
        userIdMatch = reUserId.match(watchlist_url)
        listIdMatch = reListId.match(watchlist_url)
        
        if userIdMatch and listIdMatch:
            query = {"list_id" : listIdMatch.groups()[0],
                 "list_class" : "WATCHLIST", 
                 "view" : "compact", 
                 "list_type" : "Titles", 
                 "filter" : '{"title_type":["tv_series"]}', 
                 "sort_field" : "created", 
                 "sort_direction" : "desc", 
                 "user_id" : userIdMatch.groups()[0]}
            return query  
                
        return False