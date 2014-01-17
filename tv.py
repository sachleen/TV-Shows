import os
import sys
import re
from datetime import datetime, date, timedelta
import sqlite3 as sql
import urllib2
from xml.dom import minidom
import webbrowser

'''
Constants
'''
MAX_TITLE_LENGTH = 20
MAX_DESC_LENGTH = 65
DB_NAME = 'test.db'

DATABASE_NAME = os.path.join(os.path.dirname(os.path.realpath(__file__)), DB_NAME)

def main():
    initDatabase()

    '''
    Update unwatched episodes list with the episodes from the feed
    '''
    updateSeries(all = True)
    
    if len(sys.argv) == 2:
        if sys.argv[1] == 'uwcount':
            episodes = getUnwatched()
            
            episodes = [(ep[1], ep[2], ep[3]) for ep in episodes if toDate(ep[5]) <= date.today()]
            
            print len(episodes)
            for ep in episodes:
               print "{0} s{1:02} e{2:02}".format(*ep)
        
        exit()
    '''
    Get user input on what to do
    '''
    print ''
    listUnwatched()
    while True:
        print ''
        print "Enter a command or h for help"
        input = raw_input(":")
        print ''
        
        if   input == 'h': printHelp()
        elif input == 'l': listUnwatched()
        elif input == 'ls': listMyShows()
        elif input == 'fr': forceUpdate()
        elif input == 'q': exit()
        elif re.match('^o\d+$', input): openLinks(int(re.search('^o(\d+)$', input).group(1)))
        elif re.match('^w\d+$', input): markWatched(int(re.search('^w(\d+)$', input).group(1)))
        elif re.match('^wall\d+$', input): markWatched(int(re.search('^wall(\d+)$', input).group(1)), True)
        elif re.match('^s[\w\s]+$', input): searchForSeries(re.search('^s([\w\s]+)$', input).group(1))
        elif re.match('^a\d+$', input): addSeries(re.search('^a(\d+)$', input).group(1))
        elif re.match('^d\d+$', input): deleteSeries(re.search('^d(\d+)$', input).group(1))
        else: print "Invalid input. Enter h for help."

def listMyShows():
    '''
    Lists all shows in the database along with their ID
    '''
    con = sql.connect(DATABASE_NAME)
    cur = con.cursor()
    cur.execute("SELECT * FROM shows;")
    shows = cur.fetchall();
    con.close()
    
    print "Found {0} results".format(len(shows))
    
    if len(shows) > 0:
        print " {0:<5} | {1}".format("ID", "Series Name")
        for show in shows:
            id = show[0]
            name = show[1].encode('utf-8')
            print " {0:<5} | {1}".format(id, name)
    
def forceUpdate():
    '''
    Force program to refresh all episode data from TVRage
    '''
    con = sql.connect(DATABASE_NAME)
    cur = con.cursor()
    cur.execute("INSERT OR REPLACE INTO settings VALUES('lastUpdate', '');")
    con.commit()
    con.close()
    updateSeries(all = True)

def updateSeries(id = [0,], all = False):
    '''
    Get latest unwatched episode data from TVRage and update database
    Parameters:
    id (list)  - List of TVRage series IDs to update
    all (bool) - True: all shows in database will be updated
                 False: Only shows specified in id list will be updated
    '''
    if all:
        # Get list of shows from database
        con = sql.connect(DATABASE_NAME)
        cur = con.cursor()
        cur.execute("SELECT id FROM shows;")
        result = cur.fetchall();
        con.close()
        
        # flatten result list
        seriesIds = [e for tup in result for e in tup]
        results = getEpisodes(seriesIds)
    else:
        results = getEpisodes(id, force = True)

    con = sql.connect(DATABASE_NAME)
    cur = con.cursor()
    for result in results:
        cur.execute("INSERT OR IGNORE INTO unwatched VALUES(?, ?, ?, ?, ?, 0)",
                    (result['id'], result['season'], result['episode'], result['description'], result['airDate']))
        con.commit()
    con.close()

def openLinks(index):
    try:
        episode = getUnwatched()[index]
        
        urls = ("http://www.newshost.co.za/?s={0}+s{1:02d}e{2:02d}", "https://www.nzbclub.com/search.aspx?q={0}+s{1:02d}e{2:02d}")
        
        print "Opening links for", episode[1]
        for url in urls:
            url = urllib2.quote(url.format(episode[1], episode[2], episode[3]), safe="%/:=&?~#+!$,;'@()*[]")
            webbrowser.open_new_tab(url)
            
    except IndexError:
        print "Invalid ID"

def searchForSeries(query):
    '''
    Display a list of show names that match the search string
    Parameters:
    query (string) - What to search for
    '''
    url = "http://services.tvrage.com/feeds/search.php?show={0}".format(query)
    url = urllib2.quote(url, safe="%/:=&?~#+!$,;'@()*[]")
    
    try:
        dom = minidom.parse(urllib2.urlopen(url, timeout=10.0))

        shows = dom.getElementsByTagName('show')
        
        print "Found {0} results".format(len(shows))
        print " {0:<5} | {1}".format("ID", "Series Name")
        
        for show in shows:
            id = show.childNodes[1].firstChild.nodeValue
            name = show.childNodes[3].firstChild.nodeValue.encode('utf-8')
            print " {0:<5} | {1}".format(id, name)
        
    except:
        print "Unexpected error or timeout"

def addSeries(id):
    '''
    Add a series to monitor unwatched episode
    Parameters:
    id (int) - ID of the series from TVRage
    '''
    url = "http://services.tvrage.com/feeds/showinfo.php?sid={0}"
    try:
        dom = minidom.parse(urllib2.urlopen(url.format(id), timeout=10.0))
        showName = dom.getElementsByTagName('showname').item(0).firstChild.nodeValue

        con = sql.connect(DATABASE_NAME)
        cur = con.cursor()
        cur.execute("INSERT OR IGNORE INTO shows VALUES(?, ?);", (id,showName))
        con.commit()
        con.close()
        print "Added", showName
        
        updateSeries(id = [id,])
    except:
        print "Unexpected error or timeout"

def deleteSeries(id):
    '''
    Delete an entire series from the database
    Parameters:
    id (int) - ID of the series from TVRage
    '''
    
    con = sql.connect(DATABASE_NAME)
    cur = con.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    con.commit()
    
    
    cur.execute("SELECT title FROM shows WHERE id = ?;", (id,))
    result = cur.fetchone()
    if result:
        cur.execute("DELETE FROM shows WHERE id = ?;", (id,))
        con.commit()
        print "Deleted", result[0]
    else:
        print "Show not found. Use ls to look up the ID"
    con.close()

def markWatched(index, allPrevious = False):
    '''
    Mark an episode as watched so it no longer appears in the list
    Parameters:
    index (int)         - Zero based index for episode to mark as watched from the list
    allPrevious (bool)  - If true all episodes in this series up to and including the one specified in index will be marked as watched
    '''
    try:
        episode = getUnwatched()[index]
        
        # Mark episode watched in database
        con = sql.connect(DATABASE_NAME)
        cur = con.cursor()
        
        if allPrevious:
            cur.execute("""UPDATE unwatched SET watched = 1
                        WHERE id = ?
                        AND ((season < ?)
                        OR (season = ? AND episode <= ?))
                        """, (episode[0], episode[2], episode[2], episode[3]))
            print "Marked {0} Season {1} Episode {2} and all previous episodes in the series as watched".format(episode[1], episode[2], episode[3])

        else:
            cur.execute("""UPDATE unwatched SET watched = 1
                        WHERE id = ?
                        AND   season = ?
                        AND   episode = ?
                        """, (episode[0], episode[2], episode[3]))
            print "Marked {0} Season {1} Episode {2} as watched".format(episode[1], episode[2], episode[3])
        con.commit()
        con.close()
        
    except IndexError:
        print "Invalid ID"

def getUnwatched():
    '''
    Get unwatched episodes
    
    Returns:
    (list) - list of unwatched episodes
    '''
    con = sql.connect(DATABASE_NAME)
    cur = con.cursor()
    cur.execute("SELECT shows.id, shows.title, season, episode, description, airDate FROM unwatched INNER JOIN shows on shows.id = unwatched.id WHERE watched = 0 ORDER BY airDate ASC, shows.title ASC;")
    data = cur.fetchall();
    con.close()

    return data

def listUnwatched():
    '''
    Display a list of unwatched episodes
    '''
    episodes = getUnwatched()
    
    if len(episodes) == 0:
        print "No unwatched episodes!"
    else:
        print " {0:3} | {1:20} | {2} | {3:10} | {4}".format("ID", "Show", "Episode", "Date", "Description")
        
        for idx, row in enumerate(episodes):
            title = (row[1][:MAX_TITLE_LENGTH-3] + '...') if len(row[1]) > MAX_TITLE_LENGTH else row[1]
            desc = (row[4][:MAX_DESC_LENGTH-3] + '...') if len(row[4]) > MAX_DESC_LENGTH else row[4]

            # Don't show ID for episodes not aired yet.
            if toDate(row[5]) > date.today():
                idx = ' - '
            
            print " {0:<3} | {1:20} | s{2:02} e{3:02} | {4} | {5}".format(idx, title, row[2], row[3], row[5], desc.encode('utf-8'))
            
            try:
                if toDate(row[5]) <= date.today() and toDate(episodes[idx+1][5]) > date.today():
                    print ''
            except:
                pass

def printHelp():
    '''
    Display help and available commands from help.txt
    '''
    try:
        with open('help.txt', 'r') as fin:
            print fin.read()
    except IOError:
        print "Help file not found :("

def initDatabase():
    '''
    Setup the SQLite database if it doesn't already exist
    '''
    con = sql.connect(DATABASE_NAME)
    with con:
        cur = con.cursor()

        cur.execute("""CREATE TABLE IF NOT EXISTS unwatched (
                    'id' INTEGER NOT NULL,
                    'season' INTEGER NOT NULL,
                    'episode' INTEGER NOT NULL,
                    'description' TEXT,
                    'airDate' TEXT NOT NULL,
                    'watched' INTEGER NOT NULL DEFAULT (0),
                    PRIMARY KEY(id, season, episode)
                    FOREIGN KEY(id) REFERENCES shows(id) ON DELETE CASCADE
                    )""")
        
        cur.execute("""CREATE TABLE IF NOT EXISTS shows (
                    'id' INTEGER NOT NULL,
                    'title' TEXT NOT NULL,
                    PRIMARY KEY (id)
                    )""")
        
        cur.execute("""CREATE TABLE IF NOT EXISTS settings (
                    'name' TEXT NOT NULL,
                    'value' TEXT NOT NULL,
                    PRIMARY KEY (name)
                    )""")
        cur.execute("INSERT OR IGNORE INTO settings VALUES('lastUpdate', '');");
        con.commit()

def getEpisodes(seriesIds, force = False):
    '''
    Get the episode list for shows
    Parameters:
    seriesIds - List of series IDs from TVRage
    
    Returns:
    List of episodes with the following information:
    id          - TVRage ID for the series
    series      - Name of the series
    season      - Season number
    episode     - Episode number in the season
    airDate     - Original air date
    description - Description for the episode
    '''
    
    # Checks if an update is necessary
    doUpdate = False
    if force:
        doUpdate = True
    else:
        con = sql.connect(DATABASE_NAME)
        cur = con.cursor()
        cur.execute("SELECT value FROM settings WHERE name = 'lastUpdate';")
        data = cur.fetchone()[0];
        con.close()
        if data:
            if toDate(data) < date.today():
                doUpdate = True
        else:
            doUpdate = True
        
    episodeList = []
    
    if doUpdate:
        print "Updating... "
        
        feedUrl = "http://www.tvrage.com/feeds/episode_list.php?sid={0}"
        
        for id in seriesIds:
            try:
                dom = minidom.parse(urllib2.urlopen("http://www.tvrage.com/feeds/episode_list.php?sid={0}".format(id), timeout=10.0))

                seriesName = dom.childNodes[0].childNodes[1].firstChild.nodeValue
                totalSeasons = int(dom.childNodes[0].childNodes[3].firstChild.nodeValue)
                
                print seriesName
                
                for season in dom.getElementsByTagName('Season'):
                    seasonNum = int(season.getAttribute('no'))
                    for episode in season.getElementsByTagName('episode'):
                        
                        episodeNumFull = episode.getElementsByTagName('epnum')[0].firstChild.nodeValue
                        episodeNum = episode.getElementsByTagName('seasonnum')[0].firstChild.nodeValue
                        airdate = episode.getElementsByTagName('airdate')[0].firstChild.nodeValue
                        title = episode.getElementsByTagName('title')[0].firstChild.nodeValue

                        # Only get episodes that have an air date and those airing up until the next week
                        nextWeek = date.today() + timedelta(days=7)
                        if airdate != "0000-00-00" and toDate(airdate) <= nextWeek:
                            episodeList.append({
                                'id': id,
                                'series': seriesName,
                                'season': int(seasonNum),
                                'episode': int(episodeNum),
                                'airDate': airdate,
                                'description': title
                            })
                
                # Update last update date in database
                con = sql.connect(DATABASE_NAME)
                cur = con.cursor()
                cur.execute("INSERT OR REPLACE INTO settings VALUES('lastUpdate', ?);", (date.today(),))
                con.commit()
                con.close()
            except:
                print "Unexpected error or timeout"
    
    return episodeList

def toDate(dateStr):
    '''
    Convert a date string to a date object
    
    Parameters:
    dateStr - date string in yyyy-mm-dd format
    
    Returns:
    date object
    '''
    try:
        return datetime.strptime(dateStr, '%Y-%m-%d').date()
    except:
        # Sometimes the date is like 2010-00-00.. weird. so just return another, valid date
        return date.today()
main()