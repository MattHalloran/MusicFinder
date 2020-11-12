# Searches youtube for the best video to take an mp3 from
# Author: Matt Halloran
# Version: 20200109
# TODO: 1) For every video, WRONG_VIDEO_WORDS gets another 'clean' appended
#       2) Some things probably don't need to get redone for every song (ex: the youtube build function)
# YoutubeSearch from https://github.com/joetats/youtube_search

import json
from utils import removeTitleJunk, words_kept_in_parens2, censor

from youtube_search import YoutubeSearch

Prefer_Explicit = True
# If these words appear in the title or publisher name, don't use these videos
WRONG_VIDEO_WORDS = ['karaoke', 'not official', 'montage', 'remix',
                     'snippet', '8d audio', 'reaction', 'review',
                     'choreography', 'fast', 'reverb', 'performs',
                     'symphony', 'orchestra', 'loop', 'live', 'stream',
                     'radio']
# If these words appear in the title, only use the video if no other option
OKAY_VIDEO_WORDS = ['music video']
# If these words appear in the title, they are likely reliable
BETTER_VIDEO_WORDS = ['audio', 'official audio']


class YoutubeResult():
    def __init__(self, data: dict):
        self.id = data['id']
        self.title = censor(data['title'])
        self.channel = data['channel']
        self.duration = self.time_to_seconds(data['duration'])
        self.views = self.views_to_number(data['views'])

    def time_to_seconds(self, time: str):
        ''' Converts time string to seconds for easy comparisons '''
        try:
            return sum(x * int(t) for x, t in zip([1, 60, 3600], reversed(time.split(":"))))
        except:
            return 0

    def views_to_number(self, views: str):
        ''' Converts view string to a number (ex: '1,234 views' -> 1234) '''
        try:
            return int(''.join(i for i in views if i.isdigit()) or 0)
        except:
            return 0


# Returns the best youtube links to use for the mp3 download.
def youtube_search(artist: str, title: str):
    BASE_URL = 'https://www.youtube.com/watch?v='
    WRONG_WORDS = WRONG_VIDEO_WORDS
    OKAY_WORDS = OKAY_VIDEO_WORDS
    BETTER_WORDS = BETTER_VIDEO_WORDS

    # Turn the YoutubeResults objects into youtube links
    def formatOutput(videos):
        return [f'{BASE_URL}{video.id}' for video in videos]

    # Create simplified song title to check for in the video title.
    # This is converted to regex to catch cases  where words are censored.
    title_without_junk = censor(removeTitleJunk(title, words_kept_in_parens2).lower())

    # If the song or artist contains a filter word, don't use that filter word
    # for this search
    WRONG_WORDS = [word for word in WRONG_VIDEO_WORDS if word not in (artist + title).lower()]
    OKAY_WORDS = [word for word in OKAY_VIDEO_WORDS if word not in (artist + title).lower()]
    if Prefer_Explicit:
        if 'clean' not in (artist + title).lower():
            WRONG_WORDS.append('clean')
        if 'censored' not in (artist + title).lower():
            WRONG_WORDS.append('censored')

    json_result = YoutubeSearch(f'{artist} {title} audio', max_results=10).to_json()

    # Filter out results that:
    # 1) contain the filter words in either the title or channel name
    # 2) don't have the artist name in either the channel name or title
    # 3) song title is not in video title
    input_dict = json.loads(json_result)
    # Gives better videos more importance when sorting.
    # Feel free to change this value
    better_weight = 1000
    better_video_data = []
    good_video_data = []
    okay_video_data = []
    for data in input_dict['videos']:
        video = YoutubeResult(data)
        if artist.lower().replace(' ', '') not in (video.channel+video.title).lower().replace(' ', ''):
            continue
        if title_without_junk not in video.title.lower():
            continue
        if any(bad in (video.channel.lower() + video.title.lower()) for bad in WRONG_WORDS):
            continue
        if any(okay in video.title.lower() for okay in OKAY_WORDS):
            okay_video_data.append(video)
        elif any(better in video.title.lower() for better in BETTER_WORDS):
            video.views = video.views * better_weight
            better_video_data.append(video)
        else:
            good_video_data.append(video)

    if len(good_video_data) == 0 and len(better_video_data) == 0 and len(okay_video_data) > 0:
        return formatOutput(okay_video_data)

    # Return the good and better videos based on view count, with better videos having more weight
    all_videos = good_video_data + better_video_data
    all_videos.sort(key=lambda video: video.views, reverse=True)
    return formatOutput(all_videos)

#print(youtube_search('Machine Gun Kelly', 'Trap Paris'))