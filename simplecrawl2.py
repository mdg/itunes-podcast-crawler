from bs4 import BeautifulSoup
import requests
from string import ascii_uppercase
import re 
import urllib.parse as urlparse
import json
import csv 
import sys
import os
import datetime

# Variablen und Konstanten
data_en = []
ids = []
podcastlinks = []
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




allcatpage = requests.get(startlink, timeout=5)
categories = BeautifulSoup(allcatpage.content, "html.parser")

# Verzeichnis für die Ergebnisdaten anlegen
savedir = "crawl_" + str(datetime.date.today())
if not os.path.exists(savedir):
    os.mkdir(savedir)

# Save links...
with open(savedir + '/' + 'allpodcastlinks.json', 'w', newline="") as outfile:
    # Arbeitsschritt 1 - wie sammeln erst mal alle podcast links auf der itunes Seite ein

    top_level_genres = categories.select('.top-level-genre')
    print(repr(top_level_genres))

    sub_genres = categories.select('.top-level-subgenres li a')
    print(str(sub_genres))

    all_genres = top_level_genres + sub_genres

    for category in all_genres: # Loop through all genres
        itunesGenre = category.get_text()
        print (itunesGenre)

        categorypage = requests.get(category['href'], timeout=5)

        allpodcasts = BeautifulSoup(categorypage.content, 'html.parser')
        allpodcastlinks = allpodcasts.select('#selectedcontent ul>li a')
        linkcount = len(allpodcastlinks)

        for link in allpodcastlinks: # Finally! We loop through all podcast links! Yey!
            title = link.get_text()
            print("\t"+title)
            if "/id" in link['href']:
                theID = get_id(link['href'])

                # Duplikate ausschließen
                if not theID in ids:
                    ids.append(theID)
                    linkinfo = {
                        "link": link['href'],
                        "itunesID": theID
                    }
                    podcastlinks.append(linkinfo)

                    all_podcasts[theID] = {
                        "link": link['href'],
                        "itunesID": theID,
                        "title": title,
                    }

            # for page in pagedletterpage.select('.paginate a'): # sub-subpages from 1-x
            #     podcastpage = requests.get(page['href'], timeout=5)
            #     allpodcasts = BeautifulSoup(podcastpage.content, 'html.parser')

            #     for link in allpodcasts.select('#selectedcontent ul>li a'): # Finally! We loop through all podcast links! Yey!
            #         if "/id" in link['href']:
            #             theID = get_id(link['href'])

            #             # Duplikate ausschließen
            #             if not theID in ids:
            #                 ids.append(theID)
            #                 linkinfo = {
            #                     "link": link['href'],
            #                     "itunesID": theID
            #                 }
            #                 podcastlinks.append(linkinfo)

    print('json dump to outfile\n')
    # print(json.dumps(podcastlinks))
    json.dump(all_podcasts, outfile, indent=3)
