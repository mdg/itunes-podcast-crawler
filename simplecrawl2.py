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
            print(title)
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


exit(0)

# Arbeitsschritt 2 - via itunes Lookup API Podcast Details abrufen 
for link in podcastlinks:
    print("lookup link: "+ json.dumps(link))

    try:
        theID = str(link["itunesID"])

        lookupurl = 'https://itunes.apple.com/us/lookup?id=' + theID

        try: 
            luresults = requests.get(lookupurl, timeout=5).json()
            if 'feedUrl' not in luresults['results'][0]:
                # es gibt keine gültige feedURL, wir gehen also zum nächsten Eintrag
                print ("+++++++++ keine gültige Feedurl für ID" + theID + " +++++++++")
                continue

            # wir haben also eine FeedURL, versuchen wir doch mal drauf zuzugreifen...
            itunesData = requests.get(lookupurl, timeout=5).json()['results'][0]
            feedurl = itunesData['feedUrl']
        except:
            # Autsch, Fehler. Könnte man jetzt trotzdem ablegen, werden wir aber nicht...
            print ("+++++++++ Fehler beim Zugriff auf " + lookupurl + " +++++++++")
            # continue

        

        # jetzt wissen wir den Podcastfeed und den laden wir jetzt.
        try: 
            xmlfeed = requests.get(feedurl, timeout=5)
            xf = BeautifulSoup(xmlfeed.content, 'xml')
            primaryGenreName = itunesData["primaryGenreName"]
            releaseDate = itunesData["releaseDate"]
            title = xf.channel.title.get_text()

            try:
                language = xf.channel.language.get_text()
            except:
                language = "UNKNOWN"

            episodecount = str(len(xf.find_all("item")))
        except:
            print ("+++++++++ Fehler beim Zugriff auf oder der Auswertung von " + feedurl + " +++++++++")
            # continue
        
        try:
            description = xf.channel.description.get_text()
        except:
            description = ""

        try:
            wlink = xf.channel.link.get_text()
        except:
            wlink = ""

        try: 
            author = xf.find("itunes:author").get_text()
        except:
            author = ""

        nl = urlparse.urlsplit(feedurl).netloc

        metadata = {
            "title": title,
            "description": description,
            "feedurl": feedurl,
            "itunesGenre": primaryGenreName,
            "itunesID": theID,
            "episodecount": episodecount,
            "link": wlink,
            "author": author,
            "language": language,
            "feeddomain": ".".join(nl.split('.')[-2:]),
            "feedtld": ".".join(nl.split('.')[-1:]),
            "releaseDate": releaseDate,
            "releaseyear": releaseDate[0:4]
        }

        if 'en-' in language.lower():
            data_en.append(metadata)

        if language.lower() == 'en':
            data_en.append(metadata)

        print (title)


    except:
        print("+++++++++ Oops! ",sys.exc_info()[0]," occured. +++++++++")
        # continue

# jetzt speichern wir unsere finalen Ergebnisse ab
saveall()

