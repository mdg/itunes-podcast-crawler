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
data_all = []
data_en = []
data_de = []
data_all_2019 = []
ids = []
podcastlinks = []
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
    # print ("saving data_all...")
    # savedata(data_all, savedir + '/' + 'data_all.json')
    # print ("done.")

    print ("saving data_en...")
    savedata(data_en, savedir + '/' + 'data_en.json')
    print ("done.")
    
    # print ("saving data_de...")
    # savedata(data_de, savedir + '/' + 'data_de.json')
    # print ("done.")
    
    # print ("saving data_all_2019...")
    # savedata(data_all_2019, savedir + '/' + 'data_all_2019.json')
    # print ("done.")
    
    # flush memory
    data_all.clear()
    data_en.clear()
    data_de.clear()
    data_all_2019.clear()




allcatpage = requests.get(startlink, timeout=5)
categories = BeautifulSoup(allcatpage.content, "html.parser")

# Verzeichnis für die Ergebnisdaten anlegen
savedir = "crawl_" + str(datetime.date.today())

if True or not os.path.exists(savedir):
    if not os.path.exists(savedir):
        os.mkdir(savedir)

    # Arbeitsschritt 1 - wie sammeln erst mal alle podcast links auf der itunes Seite ein
    for category in categories.select('.top-level-genre'): # Loop through all genres
        print("get category "+ category['href'])
        categorypage = requests.get(category['href'], timeout=5)
        alphabetpages = BeautifulSoup(categorypage.content, "html.parser")
        itunesGenre = category.get_text()
        print (itunesGenre)

        # for letter in ascii_uppercase: # Subpages from A-Z + ÄÖÜ + *
        for letter in ['A', 'B', 'C']:
            print("get letter "+ letter)
            letterpageurl = category['href'] + "&letter=" + letter
            letterpage = requests.get(letterpageurl, timeout=5)
            pagedletterpage = BeautifulSoup(letterpage.content, 'html.parser')
            print (itunesGenre + " - " + letter)

            pgcount = 1
            linkcount = 1

            while linkcount>0:
                print (pgcount)
                pgurl = letterpageurl + "&page=" + str(pgcount)
                pgcount += 1

                podcastpage = requests.get(pgurl, timeout=5)
                allpodcasts = BeautifulSoup(podcastpage.content, 'html.parser')
                allpodcastlinks = allpodcasts.select('#selectedcontent ul>li a')
                linkcount = len(allpodcastlinks)

                for link in allpodcastlinks: # Finally! We loop through all podcast links! Yey!
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

                if linkcount == 1: # Bug in itunes: Jede page hat mindestens einen podcast, egal wie hoch die Paginierungszahl. Eine Seite mit nur einem Podcast ist also garantiert die letzte.
                    linkcount = 0

                if pgcount > 5:
                    break

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


    # Save links...
    with open(savedir + '/' + 'allpodcastlinks.json', 'w', newline="") as outfile:
        print('json dump to outfile\n')
        json.dump(podcastlinks, outfile)
else: # oh, the folder exists from an earlier crawl? Let's use it!
    with open(savedir + '/' + 'allpodcastlinks.json', "r") as read_file:
        podcastlinks = json.load(read_file)
     
# Arbeitsschritt 2 - via itunes Lookup API Podcast Details abrufen 
for link in podcastlinks:
    print("lookup link: "+ link)

    try:
        theID = str(link["itunesID"])

        lookupurl = 'https://itunes.apple.com/de/lookup?id=' + theID

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
            continue

        

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
            continue
        
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

        # if 'de-' in language.lower():
        #     data_de.append(metadata)

        # if language.lower() == 'de':
        #     data_de.append(metadata)

        # if '2019' in releaseDate:
        #     data_all_2019.append(metadata)

        # data_all.append(metadata)
        print (title)


    except:
        print("+++++++++ Oops! ",sys.exc_info()[0]," occured. +++++++++")
        continue

# jetzt speichern wir unsere finalen Ergebnisse ab
saveall()

