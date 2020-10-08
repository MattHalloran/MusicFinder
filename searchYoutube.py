# Searches youtube for the best video to take an mp3 from
# Author: Matt Halloran
# Version: 20200109
# TODO: 1) For every video, WRONG_VIDEO_WORDS gets another 'clean' appended
#       2) Some things probably don't need to get redone for every song (ex: the youtube build function)
# YoutubeSearch from https://github.com/joetats/youtube_search

import json
from utils import removeTitleJunk, words_kept_in_parens2

from youtube_search import YoutubeSearch

Prefer_Explicit = True
# If these words appear in the title or publisher name, don't use these videos
WRONG_VIDEO_WORDS = ['karaoke', 'not official', 'montage', 'remix',
                     'snippet', '8d audio', 'reaction', 'review',
                     'choreography', 'fast', 'reverb']


# Converts time string to seconds for easy comparisons
def time_to_seconds(time: str):
    return sum(x * int(t) for x, t in zip([1, 60, 3600], reversed(time.split(":"))))


# Converts view string to a number (ex: '1,234 views' to 1234)
def views_to_number(views: str):
    print(views)
    return int(''.join(i for i in views if i.isdigit()) or 0)


# Returns the best youtube link to use for the mp3 download.
# Favors reasonably short videos that aren't clean
def youtube_search(artist: str, title: str):
    global WRONG_VIDEO_WORDS

    BASE_URL = 'https://www.youtube.com/watch?v='

    title_without_junk = removeTitleJunk(title, words_kept_in_parens2).lower()

    if Prefer_Explicit and 'clean' not in (artist + title).lower():
        WRONG_VIDEO_WORDS.append('clean')

    # If the song or artist contains a filter word, don't use that filter word
    # for this search
    WRONG_VIDEO_WORDS = [word for word in WRONG_VIDEO_WORDS if word not in (artist + title).lower()]

    json_result = YoutubeSearch(f'{artist} {title} audio', max_results=10).to_json()

    # Filter out results that:
    # 1) contain the filter words in either the title or channel name
    # 2) don't have the artist name in either the channel name or title
    # 3) song title is not in video title
    input_dict = json.loads(json_result)
    video_data = []
    for x in input_dict['videos']:
        channel = x['channel']
        videoTitle = x['title']
        duration = time_to_seconds(x['duration'])
        if artist.lower() not in (channel+videoTitle).lower():
            continue
        if title_without_junk not in videoTitle.lower():
            continue
        if any(bad in (channel.lower() + videoTitle.lower()) for bad in WRONG_VIDEO_WORDS):
            continue
        video_data.append([x['id'],
                          videoTitle,
                          duration,
                          views_to_number(x['views'])])

    # Find any videos claiming to be official audio
    official_audio_videos = []
    if 'audio' not in title_without_junk:
        for i, video in enumerate(video_data, 1):
            video_title = video[1].lower()
            if 'audio' in video_title and title_without_junk in video_title:
                official_audio_videos.append(video)
    if len(official_audio_videos) > 0:
        video_data = official_audio_videos

    # Return the video with the highest views
    highest_view_count = max([video[3] for video in video_data])
    view_count_filter = [video for video in video_data if video[3] == highest_view_count]
    return f'{BASE_URL}{view_count_filter[0][0]}'
