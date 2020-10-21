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
                     'choreography', 'fast', 'reverb', 'performs',
                     'symphony', 'orchestra', 'loop']
# If these words appear in the title, only use the video if no other option
OKAY_VIDEO_WORDS = ['music video']
# If these words appear in the title, they are likely reliable
BETTER_VIDEO_WORDS = ['audio', 'official audio']
# The highest acceptable difference in duration between videos claiming to be
# official audio, and a video with high views


class YoutubeResult():
    def __init__(self, data: dict):
        self.id = data['id']
        self.title = data['title']
        self.channel = data['channel']
        self.duration = self.time_to_seconds(data['duration'])
        self.views = self.views_to_number(data['views'])

    def time_to_seconds(self, time: str):
        ''' Converts time string to seconds for easy comparisons '''
        return sum(x * int(t) for x, t in zip([1, 60, 3600], reversed(time.split(":"))))

    def views_to_number(self, views: str):
        ''' Converts view string to a number (ex: '1,234 views' -> 1234) '''
        return int(''.join(i for i in views if i.isdigit()) or 0)


# Returns the best youtube link to use for the mp3 download.
def youtube_search(artist: str, title: str):
    BASE_URL = 'https://www.youtube.com/watch?v='
    WRONG_WORDS = WRONG_VIDEO_WORDS
    OKAY_WORDS = OKAY_VIDEO_WORDS
    BETTER_WORDS = BETTER_VIDEO_WORDS

    # Turn the video id into a youtube link
    def formatOutput(video: YoutubeResult):
        return f'{BASE_URL}{video.id}'

    title_without_junk = removeTitleJunk(title, words_kept_in_parens2).lower()

    if Prefer_Explicit and 'clean' not in (artist + title).lower():
        WRONG_WORDS.append('clean')

    # If the song or artist contains a filter word, don't use that filter word
    # for this search
    WRONG_WORDS = [word for word in WRONG_VIDEO_WORDS if word not in (artist + title).lower()]
    OKAY_WORDS = [word for word in OKAY_VIDEO_WORDS if word not in (artist + title).lower()]

    json_result = YoutubeSearch(f'{artist} {title} audio', max_results=10).to_json()

    # Filter out results that:
    # 1) contain the filter words in either the title or channel name
    # 2) don't have the artist name in either the channel name or title
    # 3) song title is not in video title
    input_dict = json.loads(json_result)
    good_video_data = []
    okay_video_data = []
    for data in input_dict['videos']:
        video = YoutubeResult(data)
        if artist.lower() not in (video.channel+video.title).lower():
            continue
        if title_without_junk not in video.title.lower():
            continue
        if any(bad in (video.channel.lower() + video.title.lower()) for bad in WRONG_WORDS):
            continue
        if any(okay in video.title.lower() for okay in OKAY_WORDS):
            okay_video_data.append(video)
        else:
            good_video_data.append(video)

    if len(good_video_data) == 0:
        if len(okay_video_data) > 0:
            return formatOutput(okay_video_data[0])
        return None

    # Find any videos claiming to be official audio or lyric videos,
    # as these are often reliable
    better_video_data = []
    BETTER_WORDS = [word for word in BETTER_WORDS if word not in title_without_junk]
    for i, video in enumerate(good_video_data, 1):
        if any(good in video.title.lower() for good in BETTER_WORDS) and title_without_junk in video.title.lower():
            better_video_data.append(video)

    # Return the video with the highest views, or one of the more reliable videos
    # if it has a decent number of views relative to the highest
    highest_good_view_count = max([video.views for video in good_video_data])
    good_view_count_filter = [video for video in good_video_data if video.views == highest_good_view_count]
    if len(better_video_data) > 0:
        highest_better_view_count = max([video.views for video in better_video_data])
        better_view_count_filter = [video for video in better_video_data if video.views == highest_better_view_count]
        # If most viewed video has less than 1000 times the views
        if highest_good_view_count / highest_better_view_count < 1000:
            return formatOutput(better_view_count_filter[0])
    return formatOutput(good_view_count_filter[0])

print(youtube_search('Machine Gun Kelly', 'Trap Paris'))