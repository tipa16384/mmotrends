#!/usr/bin/python

from pytrends.request import TrendReq
from time import time, sleep
from random import random, randint

# name of the file containing our MMO names
namefile = 'names.txt'

# name of the file to write the output. More popular MMOs will be
# located before less popular MMOs.
rankfile = 'rankings.txt'

# Get the trends API
pytrends = TrendReq(hl='en-US', tz=360)

# Google Trends category for MMOs
# See: https://github.com/pat310/google-trends-api/wiki/Google-Trends-Categories
mmocat = 935

# maximum games in one request
max_size = 5

# Time in seconds to wait before asking Google Trends for something.
# Otherwise, we run out of quota.
spacingDuration = 60
requestSpacing = 0
lastCallTime = 0

# timeframe -- last three months
timeframe = 'today 3-m'

# MMOs to compare written to mmolist
mmolist = {}
mmolist_names = []
with open(namefile, 'r') as f:
    for name in f.read().split('\n'):
        mmolist[name] = { 'lt': [], 'gt': [] }
        mmolist_names.append(name)

# hack to replace standard comparison function with one I define
def cmp_to_key(mycmp):
    'Convert a cmp= function into a key= function'
    class K:
        def __init__(self, obj, *args):
            self.obj = obj
        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0
        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0
        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0
        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0
        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0
        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0
    return K

def gaugeInterest(gamedata):
    """
    Return the average interest, as reported by Google Trends, for the game date
    given. This can range from 0 to 100.
    """
    numrows = len(gamedata)
    sum = 0
    for i in range(numrows):
        sum = sum + gamedata[i]
    return sum / numrows

def compareInterestOverTime(gamea, gameb):
    """
    Compare the relative interest between two games.
    1. Google Trends allows only a small number of calls per some time period. If we
       make just one call a minute, we're fine, so throttle our requests to that.
    2. Pass the games to Google Trends. It returns a dictionary keyed off the game
       name containing a list of dictionaries keyed off date. The value for each
       entry is the interest for that day.
    3. The return value is the average interest for game B less the average interest
       for game A. This sorts the game with the greater interest first.
    If there is an error, print the error and just return the interest in the two
    games as equal. The error seems to be if one game name is blank, or we have overrun
    our quota and Google Trends is through with us for a minute.
    """
    global lastCallTime, requestSpacing, spacingDuration
    try:
        now = time()
        waittime = now - lastCallTime
        lastCallTime = now
        if waittime < requestSpacing:
            interval = requestSpacing - waittime + 1
            print ('Games={}, {} -- Sleeping for {} seconds'.format(gamea, gameb, interval))
            sleep(interval)
            if random() > 0.95:
                print ('Dropping the sleep and taking our chances')
                requestSpacing = 0

        pytrends.build_payload([gamea, gameb], cat=mmocat, timeframe=timeframe, geo='', gprop='')
        data = pytrends.interest_over_time()
        gameAInterest = gaugeInterest(data[gamea]) if gamea in data else 0
        gameBInterest = gaugeInterest(data[gameb]) if gameb in data else 0
        return gameBInterest - gameAInterest
    except Exception as err:
        print ('Error was {}'.format(err))
        requestSpacing = spacingDuration
        print ('Died with error. Games are {}, {}. Spacing set to {}'.format(gamea, gameb, requestSpacing))
        sleep(requestSpacing)
        return compareInterestOverTime(gamea, gameb)

def old_sort_games():
    'Sort the game list by relative interest'
    return sorted(mmolist, key=cmp_to_key(compareInterestOverTime))

def get_chunks():
    first = 0
    last = len(mmolist)

    while first < last:
        chunk = first + max_size
        if chunk > last: chunk = last
        yield (first, chunk)
        first = first + max_size - 1

def get_relative_values(chunk_list):
    values = []
    for game in chunk_list:
        values.append(len(game))
    return values

def threaded_compare(a,b):
    if b in mmolist[a]['lt']: return -1
    if b in mmolist[a]['gt']: return 1
    for c in mmolist[a]['lt']:
        rc = threaded_compare(c,b)
        if rc < 0: return rc
    for c in mmolist[a]['gt']:
        rc = threaded_compare(c,b)
        if rc > 0: return rc
    return 0
    
def new_sort_games():
    for (first, last) in get_chunks():
        chunk_list = mmolist_names[first:last]
        chunk_values = get_relative_values(chunk_list)
        print (chunk_values)
        for i in range(len(chunk_list)):
            for j in range(len(chunk_list)):
                if i != j:
                    if chunk_values[i] > chunk_values[j]:
                        mmolist[chunk_list[i]]['gt'].append(chunk_list[j])
                    else:
                        mmolist[chunk_list[i]]['lt'].append(chunk_list[j])
    
    return sorted(mmolist_names, key=cmp_to_key(threaded_compare))

def rankAndWrite():
    'call sortGames to sort the games, then write the results to a file'
    # This could take awhile...
    l = new_sort_games()
    with open(rankfile, 'w') as f:
        for game in l:
            print('{}. {}'.format(l.index(game)+1, game), file=f)

# if calling as main, immediately call rankAndWrite to do the ranking.
if __name__ == "__main__":
    rankAndWrite()
