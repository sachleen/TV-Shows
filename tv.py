import re
from datetime import datetime, date
import sqlite3 as sql
import urllib2
from xml.dom import minidom

'''
Constants
'''
MAX_TITLE_LENGTH = 20
MAX_DESC_LENGTH = 65

DATABASE_NAME = 'test.db'

myShows = ("Community", "Futurama", "Graceland", "Homeland", "New Girl", "Psych", "Suits", "Amazing Race", "Simpsons", "Big Bang Theory", "Parks and Recreation", "Walking Dead")
feeds = ("http://www.tvrage.com/myrss.php", "http://www.tvrage.com/myrss.php?date=tomorrow", "http://www.tvrage.com/myrss.php?date=yesterday")

seriesIds = ("8322", "21686", "8511", "22589", "10188")

def main():
    initDatabase()

    con = sql.connect(DATABASE_NAME)
    cur = con.cursor()
    
    '''
    Get list of shows from database
    '''
    cur.execute("SELECT * FROM shows;")
    result = cur.fetchall();
    # flatten result list
    seriesIds = [e for tup in result for e in tup]
    
    '''
    Update unwatched episodes list with the episodes from the feed
    '''
    results = getEpisodes(seriesIds)
    for result in results:
        cur.execute("INSERT OR IGNORE INTO unwatched VALUES(?, ?, ?, ?, ?, 0)",
                    (result['series'], result['season'], result['episode'], result['description'], result['airDate']))
        con.commit()
    con.close()

    '''
    Get user input on what to do
    '''
    while True:
        unwatchedEpisodes = getUnwatched()
        
        print ''
        listUnwatched(unwatchedEpisodes)
        
        print ''
        print "Enter a command or h for help"
        input = raw_input(":")
        print ''
        
        if   input == 'h': printHelp()
        elif input == 'l': continue
        elif input == 'q': exit()
        elif re.match('^o\d+$', input): openLinks(unwatchedEpisodes, int(re.search('^o(\d+)$', input).group(1)))
        elif re.match('^w\d+$', input): markWatched(unwatchedEpisodes, int(re.search('^w(\d+)$', input).group(1)))
        elif re.match('^wall\d+$', input): markWatched(unwatchedEpisodes, int(re.search('^wall(\d+)$', input).group(1)), True)
        elif re.match('^s[\w\s]+$', input): searchForSeries(re.search('^s([\w\s]+)$', input).group(1))
        elif re.match('^a\d+$', input): addSeries(re.search('^a(\d+)$', input).group(1))
        elif re.match('^d\d+$', input): deleteSeries(re.search('^d(\d+)$', input).group(1))
        else: print "Invalid input. Enter h for help."

def openLinks(data, index):
    try:
        episode = data[index]
        print "Open ", episode
    except IndexError:
        print "Invalid ID"

def searchForSeries(query):
    url = "http://services.tvrage.com/feeds/search.php?show={0}"
    
    dom = minidom.parse(urllib2.urlopen(url.format(query), timeout=5.0))
    shows = dom.getElementsByTagName('show')
    
    print "Found {0} results".format(len(shows))
    print " {0:<5} | {1}".format("ID", "Series Name")
    
    for show in shows:
        id = show.childNodes[1].firstChild.nodeValue
        name = show.childNodes[3].firstChild.nodeValue.encode('utf-8')
        print " {0:<5} | {1}".format(id, name)

def addSeries(id):
    con = sql.connect(DATABASE_NAME)
    cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO shows VALUES(?);", (id,))
    con.commit()
    con.close()
    print "Added series ID", id

def deleteSeries(id):
    print "IMPLEMENT THIS"

def markWatched(episodes, index, allPrevious = False):
    '''
    Mark an episode as watched so it no longer appears in the list
    Parameters
    episodes (list)     - List of episodes. This is the result of the SQL query to find unwatched episodes
    index (int)         - Zero based index for episode to mark as watched from the list
    allPrevious (bool)  - If true all episodes in this series up to and including the one specified in index will be marked as watched
    '''
    try:
        episode = episodes[index]
        
        # Mark episode watched in database
        con = sql.connect(DATABASE_NAME)
        cur = con.cursor()
        
        if allPrevious:
            cur.execute("""UPDATE unwatched SET watched = 1
                        WHERE show = ?
                        AND (season < ?)
                        OR (season = ? AND episode <= ?)
                        """, (episode[0], episode[1], episode[1], episode[2]))
            print "Marked {0} Season {1} Episode {2} and all previous episodes in the series as watched".format(*episode[0:3])

        else:
            cur.execute("""UPDATE unwatched SET watched = 1
                        WHERE show = ?
                        AND   season = ?
                        AND   episode = ?
                        """, (episode[0:3]))
            print "Marked {0} Season {1} Episode {2} as watched".format(*episode[0:3])
        con.commit()
        con.close()
        
    except IndexError:
        print "Invalid ID"

def getUnwatched():
    '''
    Get unwatched episodes
    
    Returns:
    data (list) - list of unwatched episodes
    '''
    con = sql.connect(DATABASE_NAME)
    cur = con.cursor()
    cur.execute("SELECT * FROM unwatched WHERE watched = 0 ORDER BY airDate ASC, show ASC;")
    data = cur.fetchall();
    con.close()
    
    return data

def listUnwatched(episodes):
    '''
    Display a list of unwatched episodes
    Parameters:
    episodes - List of episodes. This is the result of the SQL query to find unwatched episodes
    '''
    
    if len(episodes) == 0:
        print "No unwatched episodes!"
    else:
        print " {0:3} | {1:20} | {2} | {3:10} | {4}".format("ID", "Show", "Episode", "Date", "Description")
        for idx, row in enumerate(episodes):
            title = (row[0][:MAX_TITLE_LENGTH-3] + '...') if len(row[0]) > MAX_TITLE_LENGTH else row[0]
            desc = (row[3][:MAX_DESC_LENGTH-3] + '...') if len(row[3]) > MAX_DESC_LENGTH else row[3]

            print " {0:<3} | {1:20} | s{2:02} e{3:02} | {4} | {5}".format(idx, title, row[1], row[2], row[4], desc.encode('utf-8'))

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

        cur.execute("""CREATE TABLE IF NOT EXISTS [unwatched] (
                    'show' TEXT  NOT NULL,
                    'season' INTEGER  NOT NULL,
                    'episode' INTEGER  NOT NULL,
                    'description' TEXT,
                    'airDate' TEXT  NOT NULL,
                    'watched' INTEGER  NOT NULL  DEFAULT (0),
                    PRIMARY KEY ([show],[season],[episode])
                    )""")
        
        cur.execute("""CREATE TABLE IF NOT EXISTS [shows] (
                    'id' INTEGER  NOT NULL,
                    PRIMARY KEY ([id])
                    )""")

def getEpisodes(seriesIds):
    '''
    Get the episode list for shows
    Parameters:
    seriesIds - List of series IDs from TVRage
    
    Returns:
    List of episodes with the following information:
    series      - Name of the series
    season      - Season number
    episode     - Episode number in the season
    airDate     - Original air date
    description - Description for the episode
    '''
    feedUrl = "http://www.tvrage.com/feeds/episode_list.php?sid={0}"
    
    episodeList = []
    
    print "Updating... "
    
    for id in seriesIds:
        dom = minidom.parse(urllib2.urlopen("http://www.tvrage.com/feeds/episode_list.php?sid={0}".format(id), timeout=5.0))
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
                
                # Ignore future episodes with no air date
                if airdate != "0000-00-00" and toDate(airdate) < date.today():
                    episodeList.append({
                        'series': seriesName,
                        'season': int(seasonNum),
                        'episode': int(episodeNum),
                        'airDate': airdate,
                        'description': title
                    })
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