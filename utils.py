#These characters will be excluded from file names:
# #%&{}\\/<>*?$!\'\":@+`|=
# Some will be replaced with similar-looking, valid characters (ex: $ -> S)
bad_char_map = {
    '$'  : 'S',
    '/'  : ' ',
    '#'  : '',
    '%'  : '',
    '&'  : 'and',
    '\\' : ' ',
    '<'  : '',
    '>'  : '',
    '*'  : '',
    '?'  : '',
    '!'  : '',
    '\'' : '',
    '\"' : '',
    ':'  : '',
    '@'  : '',
    '+'  : 'and',
    '`'  : '',
    '|'  : ' ',
    '='  : ''
}

#Cleans input for filename. NOTE: Do not pass in an entire path! This will remove slashes
def slugify(text:str):
    cleaned_text = ''
    for s in text:
        if s in bad_char_map:
            cleaned_text += bad_char_map[s]
        else:
            cleaned_text += s
    return cleaned_text


#****************************************************************************************************
#Helps find lyrics to songs, albums for songs, etc.
#Certain parts of the code work better when parts of the title are removed
#options for title cleaning
excludes_list1 = {"feat", "instrumental"} #checking for lyrics, probably TODO check for completeness
excludes_list2 = { } #checking for album #TODO check for completeness
#Ex: Lose Yourself (From 8 Mile Soundtrack) -> Lose Yourself
#Ex: Song A (feat. Artist B) -> No change
#Ex: Song Z (Instrumental) -> No change (don't want lyrics on an instrumental)
def removeTitleJunk(title:str, excludes_list):
    if title is None:
        return title
    title = str.strip(title.split('|')[0]) #Some songs (ex. BLACK BALLOONS | 13LACK 13ALLOONZ) have a pipe in them. For simplicity, remove that crap TODO:removes features. Should not do that
    openParenPos = title.find('(')
    if openParenPos <= 0 or openParenPos >= len(title) - 1: #return unchanged
        return title
    inParensText = title[openParenPos:].lower()
    if any(s in inParensText for s in excludes_list):
        return title #If any of the words in excludes_list is inside the parentheses, keep the parenthesis text
    return str.strip(title[0:openParenPos-1])
#****************************************************************************************************