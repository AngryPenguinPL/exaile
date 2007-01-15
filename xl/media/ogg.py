import mutagen.oggvorbis

def get_tag(f, tag):
    """
        Gets a specific tag, or if the tag does not exist, it returns an empty
        string
    """
    try:
        return unicode(f[tag][0])
    except:
        return ""

def write_tag(tr):
    try:
        com = mutagen.oggvorbis.OggVorbis(tr.loc)
    except mutagen.oggvorbis.OggVorbisHeaderError:
        com = mutagen.oggvorbis.OggVorbis()
    com.clear()
    com['artist'] = tr.artist
    com['album'] = tr.album
    com['title'] = tr.title
    com['genre'] = tr.genre
    com['tracknumber'] = str(tr.track)
    com['tracktotal'] = str(tr.disc_id)
    com['date'] = str(tr.year)
    com.save(tr.loc)

def fill_tag_from_path(tr):
    """
        Fills the passed in media.Track with tags from the file
    """
    try:
        f = mutagen.oggvorbis.OggVorbis(tr.loc)
    except mutagen.oggvorbis.OggVorbisHeaderError:
        return

    tr.length = int(f.info.length)
    tr.bitrate = int(f.info.bitrate / 1024)

    tr.artist = get_tag(f, 'artist')
    tr.album = get_tag(f, 'album')
    tr.title = get_tag(f, 'title')
    tr.genre = get_tag(f, 'genre')
    tr.track = get_tag(f, 'tracknumber')
    tr.disc_id = get_tag(f, 'tracktotal')
    tr.year = get_tag(f, 'date')
