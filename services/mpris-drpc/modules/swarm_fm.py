import os
import re
from logging import Logger

def stop_screwing_with_my_setup(metadata: dict, logger: Logger, icon_location: str = os.path.join(os.environ.get('XDG_RUNTIME_DIR', '/tmp'), 'general_thumb')):
    metadata = metadata.copy()
    metadata['mpris:artUrl'] = icon_location
    metadata['enhancements:localArtUrl'] = icon_location
    metadata['xesam:title'] = 'Swarm FM'
    metadata['xesam:artist'] = ['boop.', 'Neuro-Sama', 'Evil Neuro', 'Vedal987', 'QueenPb', 'Various']
    return metadata

def stop_screwing_with_my_setup_2(metadata: dict, logger: Logger):
    metadata = metadata.copy()
    metadata['xesam:title'] = 'Swarm FM'
    metadata['xesam:artist'] = ['boop.', 'Neuro-Sama', 'Evil Neuro', 'Vedal987', 'QueenPb', 'Various']
    return metadata

def neuro_karaoke_archive(metadata:dict, logger:Logger):
    metadata = metadata.copy()
    artist_list = []
    for artist in metadata.get('xesam:artist', []):
        artist_list.extend([artist] if '(feat. ' not in artist else [i.strip() for i in artist.replace(')', '').split('(feat. ')])
    artist_list = list(dict.fromkeys(artist_list))
    metadata['xesam:artist'] = artist_list
    metadata['xesam:title'] = re.sub('\((Duet|Evil|[Vv][0-9](\.[0-9])?)\)', '', metadata['xesam:title']).strip()
    return metadata