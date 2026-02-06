from logging import Logger

def fix_artists(metadata: dict, logger: Logger):
    metadata = metadata.copy()
    artists = []
    for i in metadata['xesam:artist']:
        for a in i.split('&'):
            artists.append(a.strip())
    metadata['xesam:artist'] = artists
    return metadata