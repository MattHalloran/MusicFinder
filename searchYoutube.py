#Searches youtube for the best video to take an mp3 from
#Author: Matt Halloran
#Version: 20200109
#TODO: 1) For every video, WRONG_VIDEO_WORDS gets another 'clean' appended
#      2) Some things probably don't need to get redone for every song (ex: the youtube build function)
#YoutubeSearch from https://github.com/joetats/youtube_search

import json
import numpy as np
import re, htmlentitydefs
from utils import removeTitleJunk, excludes_list2

from youtube_search import YoutubeSearch

Prefer_Explicit = True
WRONG_VIDEO_WORDS = ['karaoke', 'not official', 'montage', 'remix', 'snippet', '8d audio', 'reaction', 'review', 'choreography', 'fast', 'reverb'] #If these words appear in the title or publisher name, don't use these videos

#Converts time string to seconds for easy comparisons
def time_to_seconds(time:str):
    return sum(x * int(t) for x, t in zip([1, 60, 3600], reversed(time.split(":"))))

#Returns the best youtube link to use for the mp3 download.
#Favors reasonably short videos that aren't clean
def youtube_search(artist:str, title:str):
    global WRONG_VIDEO_WORDS

    title_without_junk = removeTitleJunk(title, excludes_list2).lower()

    if Prefer_Explicit and 'clean' not in (artist + title).lower():
        WRONG_VIDEO_WORDS.append('clean')

    #If the song or artist contains a filter word, don't use that filter word 
    #for this search
    WRONG_VIDEO_WORDS = [word for word in WRONG_VIDEO_WORDS if word not in (artist + title).lower()]

    json_result = YoutubeSearch(f'{artist} {title} audio', max_results=10).to_json()

    #Filter out results that:
    # 1) contain the filter words in either the title or channel name
    # 2) don't have the artist name in either the channel name or title
    # 3) song title is not in video title
    input_dict = json.loads(json_result)
    video_data = []
    for x in input_dict['videos']:
        channel = x['channel']
        videoTitle = x['title']
        duration = time_to_seconds(x['duration'])
        if not artist.lower() in (channel+videoTitle).lower():
            continue
        if not title_without_junk in videoTitle.lower():
            continue
        if any(bad in (channel.lower() + videoTitle.lower()) for bad in WRONG_VIDEO_WORDS):
            continue
        video_data.append([x['id'], videoTitle, duration])


    #Finds the duration of each video. This + the known duration of the video determines the best youtube video to download
    official_audio_videos = []
    for i in range(len(video_data)):
        if 'official audio' in video_data[i][1].lower() and title_without_junk in video_data[i][1].lower():
            official_audio_videos.append(video_data[i])

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