#Searches youtube for the best video to take an mp3 from
#Author: Matt Halloran
#Version: 20200109
#TODO: 1) For every video, WRONG_VIDEO_WORDS gets another 'clean' appended
#      2) Some things probably don't need to get redone for every song (ex: the youtube build function)

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import numpy as np
import re, htmlentitydefs
import isodate
from globals import YOUTUBE_KEY
from utils import removeTitleJunk, excludes_list2

Prefer_Explicit = True
WRONG_VIDEO_WORDS = ['karaoke', 'not official', 'montage', 'remix', 'snippet', '8d audio', 'reaction', 'review', 'choreography', 'fast', 'reverb'] #If these words appear in the title or publisher name, don't use these videos

YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

##
# Removes HTML or XML character references and entities from a text string.
# Taken from http://effbot.org/zone/re-sub.htm#unescape-html
# @param text The HTML (or XML) source text.
# @return The plain text, as a Unicode string, if necessary.
def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return chr(int(text[3:-1], 16))
                else:
                    return chr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = chr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub('&#?\w+;', fixup, text)

#Converts ISO-8601 string to seconds for easy comparisons
#Ex: PT4M13S -> 4min, 13sec -> 253sec
def time_to_seconds(time:str):
    iso_duration = isodate.parse_duration(time)
    return iso_duration.total_seconds()

#Returns the best youtube link to use for the mp3 download.
#Favors reasonably short videos that aren't clean
def youtube_search(artist:str, title:str):
    global WRONG_VIDEO_WORDS

    title_without_junk = removeTitleJunk(title, excludes_list2).lower()

    if Prefer_Explicit and 'clean' not in (artist + title).lower():
        WRONG_VIDEO_WORDS.append('clean')

    #Make sure songs and artists that contain words that usually indicate a bad video
    #don't exclude the bad words they contain (weird wording but I hope it makes sense)
    WRONG_VIDEO_WORDS = [word for word in WRONG_VIDEO_WORDS if word not in (artist + title).lower()]

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                    developerKey=YOUTUBE_KEY)

    #Searches youtube for "[ARTIST] [TRACK] lyrics" and gets every video ID
    search_response = youtube.search().list(
        q=f'{artist} {title} audio',
        part='id,snippet',
        maxResults=25,
        relevanceLanguage='en',
        safeSearch='none',
        type='video'
    ).execute()
    video_data = []
    official_audio_videos = [] #May be multiple videos that claim to have "official" audio. Some are better than others
    for search_result in search_response.get('items', []):
        channelName = search_result['snippet']['channelTitle']
        videoTitle = unescape(search_result['snippet']['title'])
        videoID = search_result['id']['videoId']
        if not artist.lower() in (channelName + videoTitle).lower():
            continue
        #Ignore result if basic song title (ex: The Moment, if title is The Moment (feat. Some Guy)) is not in video title
        if not title_without_junk in videoTitle.lower():
            continue
        #Ignore result if title or channel contains certain words
        if any(bad in (channelName.lower() + videoTitle.lower()) for bad in WRONG_VIDEO_WORDS):
            continue
        video_data.append([videoID,
                            videoTitle,
                            -1])

    #Finds the duration of each video. This + the known duration of the video determines the best youtube video to download
    videos_response = youtube.videos().list(
        part='contentDetails',
        id=','.join(x[0] for x in video_data),
        maxResults=25,
    ).execute()
    i = 0
    for data in videos_response.get('items', []):
        video_data[i][2] = time_to_seconds(data['contentDetails']['duration'])
        if 'official audio' in video_data[i][1].lower() and title_without_junk in video_data[i][1].lower():
            official_audio_videos.append(video_data[i])
        i += 1

    #If there are "official audio" videos. Return the shortest one TODO: Better way of choosing one
    if len(official_audio_videos) > 0:
        shortest = min([x[2] for x in official_audio_videos])
        official_audio_videos = [data for data in official_audio_videos if data[2] == shortest]
        return official_audio_videos[0][0]

    #Determines which video to download. Checks for:
    #1. Artist and song title must be in the title
    #2. Duration must be shortest, after removing outliers
    artist_lower = str.strip(artist.lower())
    video_data = [data for data in video_data if artist_lower in data[1].lower() and title_without_junk in data[1].lower()] #TODO might not need this if anymore
    if len(video_data) == 0: #No videos found
        return None
    #Remove videos with durations too far off from the median
    durations = [data[2] for data in video_data]
    median_duration = np.median(durations)
    video_data_shortened = [data for data in video_data if abs(data[2] - median_duration) < 20]
    #If removing durations made an empty list, use the original list. Else, use the shortened list
    if len(video_data_shortened) > 0:
        video_data = video_data_shortened
    best_duration = min([x[2] for x in video_data])
    video_data = [data for data in video_data if data[2] == best_duration]
    return video_data[0][0]



# try:
#     videos = youtube_search('travis scott', 'sicko mode') #youtube_search(artist, title)
#     #print('done')
# except HttpError as e:
#     print(f'An HTTP error occurred:\n{e}')