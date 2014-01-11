import re, feedparser
import datetime
from datetime import date
import sqlite3 as sql

myShows = ("Community", "Futurama", "Graceland", "Homeland", "New Girl", "Psych", "Suits", "Amazing Race", "Simpsons", "Big Bang Theory", "Parks and Recreation", "Walking Dead")
feeds = ("http://www.tvrage.com/myrss.php", "http://www.tvrage.com/myrss.php?date=tomorrow", "http://www.tvrage.com/myrss.php?date=yesterday")

def main():
    initDatabase()
    
    feed = 'myrss.xml'
    
    con = sql.connect('test.db')
    cur = con.cursor()
    
    '''
    Update unwatched episodes list with the episodes from the feed
    '''
    results = filterFeed(feed, myShows)
    for result in results:
        cur.execute("INSERT OR IGNORE INTO unwatched VALUES(?, ?, ?, ?, ?)",
                    (result['title'], result['season'], result['episode'], result['description'], date.today()))
        con.commit()
    
    '''
    List unwatched episodes
    '''
    cur.execute("SELECT * FROM unwatched ORDER BY airDate ASC;")
    data = cur.fetchall();

    print " {0} | {1:20} | {2} | {3:10} | {4}".format("ID", "Show", "Episode", "Date", "Description")
    for idx, row in enumerate(data):
        truncated = (row[0][:17] + '...') if len(row[0]) > 20 else row[0]
        print " {0:<2} | {1:20} | s{2:02} e{3:02} | {4} | {5}".format(idx, truncated, row[1], row[2], row[4], row[3])

    '''
    Clean up
    '''
    con.close()
    
    print ''

def initDatabase():
    """
    Setup the SQLite database if it doesn't already exist
    """
    con = sql.connect('test.db')
    with con:
        cur = con.cursor()
        
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='unwatched';")
        data = cur.fetchone()
        if data is None:
            cur.execute("""CREATE TABLE [unwatched] (
                        [show] TEXT  NOT NULL,
                        [season] INTEGER  NOT NULL,
                        [episode] INTEGER  NOT NULL,
                        [description] TEXT  NOT NULL,
                        [airDate] TEXT  NOT NULL,
                        PRIMARY KEY ([show],[season],[episode])
                        )""")

def filterFeed(feed, shows):
    """
    Loads the specified feed and finds all episodes matching the shows list
    
    Parameter   Description
    feed        URL to the TVRage RSS feed
    shows       List of shows titles to look for
    
    Returns a list of dictionaries with the following elements:
    title       Title of show
    season      Season number
    episode     Episode number
    description Episode description
    """
    
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
                        "title": title,
                        "season": int(season),
                        "episode": int(episode),
                        "description": description
                    })
    
    return showsFound

main()