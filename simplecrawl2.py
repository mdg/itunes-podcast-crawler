from bs4 import BeautifulSoup
import requests
from string import ascii_uppercase
import re 
import urllib.parse as urlparse
import json
import csv 
import sys
import operator
import os
import datetime

# Variablen und Konstanten
data_en = []
all_podcasts = {}
startlink = 'https://podcasts.apple.com/us/genre/podcasts/id26'

def get_id(url):
    parts = urlparse.urlsplit(url) 
    if parts.hostname == 'podcasts.apple.com':
        idstr = parts.path.rpartition('/')[2] # extract 'id123456'
        if idstr.startswith('id'):
            try: return int(idstr[2:])
            except ValueError: pass
        raise ValueError("Invalid url: %r" % (url,))


def savedata(the_data, filename):
    if len(the_data)>0:
        with open(filename, 'w', newline="") as outfile:
            json.dump(the_data, outfile)


def saveall():
    print ("saving data_en...")
    savedata(data_en, savedir + '/' + 'data_en.json')
    print ("done.")
    
    # flush memory
    data_en.clear()


GENRE_FILTER = [
    "Comedy",
    "Health & Fitness",
    "Kids & Family",
    "News",
    "Science",
    "Society & Culture",
    "Sports",
    "True Crime",
]


allcatpage = requests.get(startlink, timeout=5)
categories = BeautifulSoup(allcatpage.content, "html.parser")

# Verzeichnis für die Ergebnisdaten anlegen
savedir = "crawl_" + str(datetime.date.today())
if not os.path.exists(savedir):
    os.mkdir(savedir)

# Save links...
with open(savedir + '/' + 'allpodcastlinks.json', 'w') as outfile:
    # Arbeitsschritt 1 - wie sammeln erst mal alle podcast links auf der itunes Seite ein

    top_level_genres = categories.select('.top-level-genre')
    # print(repr(top_level_genres))

    genres = dict()
    for category in top_level_genres: # Loop through all genres
        itunesGenre = category.get_text()

        # skip genres not in the filter
        if itunesGenre not in GENRE_FILTER:
            continue

        print(itunesGenre)

        sub_genres = category.parent.select('.top-level-subgenres li a')
        # print(str(sub_genres))

        subs = [category]
        for subcat in sub_genres:
            print("\t"+subcat.get_text())
            subs.append(subcat)

        genres[itunesGenre] = subs

    print("\nfetch links")
    for (genre_name, category_genres) in genres.items():
        print(genre_name)
        for category in category_genres:
            subgenre_name = category.get_text()
            if genre_name == subgenre_name:
                subgenre_name = ""
            print("\t"+genre_name)
            categorypage = requests.get(category['href'], timeout=5)

            allpodcasts = BeautifulSoup(categorypage.content, 'html.parser')
            allpodcastlinks = allpodcasts.select('#selectedcontent ul>li a')
            linkcount = len(allpodcastlinks)

            rank = 0
            for link in allpodcastlinks: # Finally! We loop through all podcast links! Yey!
                rank = rank + 1
                title = link.get_text()
                print("\t\t"+title)
                if "/id" in link['href']:
                    theID = get_id(link['href'])
                    genre = {
                        "genre": genre_name,
                        "subgenre": subgenre_name,
                        "rank": rank,
                    }
                    if not theID in all_podcasts:
                        all_podcasts[theID] = {
                            "itunesID": theID,
                            "title": title,
                            "genres": [genre],
                            "link": link['href'],
                        }
                    else:
                        all_podcasts[theID]["genres"].append(genre)


    print('json dump to outfile\n')
    podlist = list(all_podcasts.values())
    podlist.sort(key=operator.itemgetter("itunesID"))
    for pod in podlist:
        json.dump(pod, outfile)
        outfile.write("\n")
