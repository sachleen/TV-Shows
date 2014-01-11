import re
import feedparser
from datetime import date
import sqlite3 as sql

'''
Constants
'''
MAX_TITLE_LENGTH = 20
MAX_DESC_LENGTH = 65

DATABASE_NAME = 'test.db'

myShows = ("Community", "Futurama", "Graceland", "Homeland", "New Girl", "Psych", "Suits", "Amazing Race", "Simpsons", "Big Bang Theory", "Parks and Recreation", "Walking Dead")
feeds = ("http://www.tvrage.com/myrss.php", "http://www.tvrage.com/myrss.php?date=tomorrow", "http://www.tvrage.com/myrss.php?date=yesterday")

def main():
    initDatabase()
    
    feed = 'myrss.xml'
    
    con = sql.connect(DATABASE_NAME)
    cur = con.cursor()
    
    '''
    Update unwatched episodes list with the episodes from the feed
    '''
    results = filterFeed(feed, myShows)
    for result in results:
        cur.execute("INSERT OR IGNORE INTO unwatched VALUES(?, ?, ?, ?, ?, 0)",
                    (result['title'], result['season'], result['episode'], result['description'], date.today()))
        con.commit()
    
    '''
    Get unwatched episodes
    '''
    cur.execute("SELECT * FROM unwatched WHERE watched = 0 ORDER BY airDate ASC, show ASC;")
    data = cur.fetchall();
    con.close()
    
    listUnwatched(data)

    '''
    Get user input on what to do
    '''
    while True:
        print ''
        print "Enter a command or h for help"
        input = raw_input(":")
        print ''
        
        if   input == 'h': printHelp()
        elif input == 'l': listUnwatched(data)
        elif input == 'q': break
        elif re.match('o\d+$', input): openLinks(data, int(re.search('o(\d+)$', input).group(1)))
        elif re.match('w\d+$', input): markWatched(data, int(re.search('w(\d+)$', input).group(1)))
        else: print "Invalid input. Enter h for help."

def openLinks(data, index):
    try:
        episode = data[index]
        print "Open ", episode
    except IndexError:
        print "Invalid ID"

def markWatched(episodes, index):
    '''
    Mark an episode as watched so it no longer appears in the list
    Parameter   Description
    episodes    List of episodes. This is the result of the SQL query to find unwatched episodes
    index       Zero based index for episode to mark as watched from the list
    '''
    try:
        episode = episodes[index]
        
        # Mark episode watched in database
        con = sql.connect(DATABASE_NAME)
        cur = con.cursor()
        cur.execute("""UPDATE unwatched SET watched = 1
                    WHERE show = ?
                    AND   season = ?
                    AND   episode = ?
                    """, (episode[0], episode[1], episode[2]))
        con.commit()
        con.close()
        
        # Remove it from the episode list
        episodes.remove(episode)
        
        print "Marked {0} Season {1} Episode {2} as watched".format(episode[0], episode[1], episode[2])
        
    except IndexError:
        print "Invalid ID"

def listUnwatched(episodes):
    '''
    Display a list of unwatched episodes
    Parameter   Description
    episodes    List of episodes. This is the result of the SQL query to find unwatched episodes
    '''

    print " {0} | {1:20} | {2} | {3:10} | {4}".format("ID", "Show", "Episode", "Date", "Description")
    for idx, row in enumerate(episodes):
        title = (row[0][:MAX_TITLE_LENGTH-3] + '...') if len(row[0]) > MAX_TITLE_LENGTH else row[0]
        desc = (row[3][:MAX_DESC_LENGTH-3] + '...') if len(row[3]) > MAX_DESC_LENGTH else row[3]
        print " {0:<2} | {1:20} | s{2:02} e{3:02} | {4} | {5}".format(idx, title, row[1], row[2], row[4], desc)

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
        
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='unwatched';")
        data = cur.fetchone()
        if data is None:
            cur.execute("""CREATE TABLE [unwatched] (
                        'show' TEXT  NOT NULL,
                        'season' INTEGER  NOT NULL,
                        'episode' INTEGER  NOT NULL,
                        'description' TEXT,
                        'airDate' TEXT  NOT NULL,
                        'watched' INTEGER  NOT NULL  DEFAULT (0),
                        PRIMARY KEY ([show],[season],[episode])
                        )""")

def filterFeed(feed, shows):
    '''
    Read the specified feed and finds all episodes matching the shows list
    
    Parameter   Description
    feed        URL to the TVRage RSS feed
    shows       List of shows titles to look for
    
    Returns a list of dictionaries with the following elements:
    title       Title of show
    season      Season number
    episode     Episode number
    description Episode description
    '''
    
    feed = feedparser.parse(feed)
    
    showsFound = []
    
    for entry in feed.entries:
        if 'summary' in entry:
            title = re.sub(r'\(\d+x\d+\)', '', entry['title'].lstrip('- ')).strip();
            description = entry['summary']
            
            search = re.search('\((\d+)x', entry['title'])
            season = search.group(1) if search else 0
            search = re.search('x(\d+)\)', entry['title'])
            episode = search.group(1) if search else 0
            
            
            for show in shows:
                if show in title:
                    showsFound.append({
                        'title': title,
                        'season': int(season),
                        'episode': int(episode),
                        'description': description
                    })
    
    return showsFound

main()