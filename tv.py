import re, feedparser

myShows = ("Community", "Futurama", "Graceland", "Homeland", "New Girl", "Psych", "Suits", "Amazing Race", "Simpsons", "Big Bang Theory", "Parks and Recreation", "Walking Dead")
feeds = ("http://www.tvrage.com/myrss.php", "http://www.tvrage.com/myrss.php?date=tomorrow", "http://www.tvrage.com/myrss.php?date=yesterday")

def main():
    for feed in feeds:
        print "Checking feed {0}".format(feed)
        
        results = filterFeed(feed, myShows)
        
        print "Found {0} episodes".format(len(results))
        
        for idx, result in enumerate(results):
            print '[{0}] {1} ({2}) - {3}'.format(idx+1, result['title'], result['episode'], result['description'])
        
        print ''

'''
    Loads the specified feed and finds all episodes matching the shows list
    Parameter   Description
    feed        URL to the TVRage RSS feed
    shows       List of shows titles to look for
    
    Returns a list of dictionaries with the following elements:
    title       Title of show
    episode     Season and Episode number in the (SSxEE) format
    description Episode description
'''
def filterFeed(feed, shows):
    feed = feedparser.parse(feed)
    
    showsFound = []
    
    for entry in feed.entries:
        if 'summary' in entry:
            title = re.sub(r'\(\d+x\d+\)', '', entry['title'].lstrip('- ')).strip();
            description = entry['summary']
            
            search = re.search('(\d+x\d+)', entry['title'])
            episodeNum = search.group(1) if search else 0
            
            
            for show in shows:
                if show in title:
                    showsFound.append({
                        "title": title,
                        "episode": episodeNum,
                        "description": description
                    })
    
    return showsFound

main()