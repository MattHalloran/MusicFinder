import difflib

bad_words = [
    'ass',
]

# These characters will be excluded from file names:
# #%&{}\\/<>*?$!\'\":@+`|=
# Some will be replaced with similar-looking, valid characters (ex: $ -> S)
bad_char_map = {
    '$': 'S',
    '/': ' ',
    '#': '',
    '%': '',
    '&': 'and',
    '\\': ' ',
    '<': '',
    '>': '',
    '*': '',
    '?': '',
    '!': '',
    '\'': '',
    '\"': '',
    ':': '',
    '@': '',
    '+': 'and',
    '`': '',
    '|': ' ',
    '=': '',
    '.': '',
    '*': '',
}

# These words get censored from the song title and video title,
# in case one of them was already censored (makes comparisons much easier)
CENSORED_WORDS = ['ass', 'fuck', 'shit', 'bitch']


# Cleans input for filename. NOTE: Do not pass in an entire path! This will remove slashes
# First tries to uncensor bad words, then removes any characters 
# not valid for file names
def slugify(text: str):
    cleaned_text = ''
    for s in text:
        if s in bad_char_map:
            cleaned_text += bad_char_map[s]
        else:
            cleaned_text += s
    return cleaned_text


# ****************************************************************************************************
# Helps find lyrics to songs, albums for songs, etc.
# Certain parts of the code work better when parts of the title are removed
# options for title cleaning
words_kept_in_parens1 = {"feat", "instrumental"}  # checking for lyrics, probably TODO check for completeness
words_kept_in_parens2 = {}  # checking for album #TODO check for completeness
# Ex: Lose Yourself (From 8 Mile Soundtrack) -> Lose Yourself
# Ex: Song A (feat. Artist B) -> No change
# Ex: Song Z (Instrumental) -> No change (don't want lyrics on an instrumental)
def removeTitleJunk(title: str, words_kept_in_parens):
    if title is None:
        return title
    title = str.strip(title.split('|')[0])  # Some songs (ex. BLACK BALLOONS | 13LACK 13ALLOONZ) have a pipe in them. For simplicity, remove that crap TODO:removes features. Should not do that
    openParenPos = title.find('(')
    if openParenPos <= 0 or openParenPos >= len(title) - 1:  # return unchanged
        return title
    inParensText = title[openParenPos:].lower()
    if any(s in inParensText for s in words_kept_in_parens):
        return title  # If any of the words in words_kept_in_parens is inside the parentheses, keep the parenthesis text
    return str.strip(title[0:openParenPos-1])
# ****************************************************************************************************


# Replace all bad words with asterisks
def censor(text: str):
    words = text.split()
    for i in range(len(words)):
        # If words is partially censored, censor the whole word
        if '*' in words[i] or words[i].lower() in CENSORED_WORDS:
            words[i] = '*'*len(words[i])
    return ' '.join(word for word in words)


# Tries to guess what bad words are, based on asterisks
def uncensor(text: str):
    words = text.split()
    for i in range(len(words)):
        if '*' in words[i]:
            # Filter bad words by length first
            possible_words = [word for word in CENSORED_WORDS if len(word) == len(words[i])]
            # Find closest match
            close_matches = difflib.get_close_matches(words[i].lower(), possible_words)
            if len(close_matches) > 0:
                words[i] = close_matches[0]
    return ' '.join(word for word in words)
