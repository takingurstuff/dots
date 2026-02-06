import os
import re
import io
import time
import logging
import requests
from logging import Logger

try:
    from PIL import Image
    pillow_avalaible = True
except (ImportError, ModuleNotFoundError):
    print('python-pillow / PIL not installed, cannot process album art, proceeding with limited functionality')
    pillow_avalaible = False

last_url = ""
last_title = ""
last_artist = [""]

def art_fetcher(url, logger: Logger, dl_attempts: int = 3, retry_cooldown: float = 0.01) -> bytes:
    """
    Downloads an image from a given URL and saves it to a specified local path.

    Args:
        url (str): The URL of the image to download.
        save_path (str): The local file path (including filename and extension)
                         where the image will be saved.
    """
    for i in range(dl_attempts):
        try:
            # Send a GET request to the URL.
            # stream=True allows us to read the content in chunks, which is good for large files.
            logger.info(f"Attempting to download image from: {url}, attempt {i+1} of {dl_attempts}")
            response = requests.get(url, stream=True)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

            return response.content
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error during network request: {e}, attempt {i+1} of {dl_attempts}")
        except IOError as e:
            logger.warning(f"Error writing file to disk: {e}, attempt {i+1} of {dl_attempts}")
        except Exception as e:
            logger.warning(f"An unexpected error occurred: {e}, attempt {i+1} of {dl_attempts}")

        time.sleep(retry_cooldown)
    return None


def get_youtube_video_id(url):
    # Regex to capture the video ID from various YouTube URL formats
    pattern = r"(?:https?://)?(?:www\.)?(?:youtube\.com/(?:[^\/\n\s]+/\S+/|(?:v|e(?:mbed)?)/|.*[?&]v=)|youtu\.be/)([a-zA-Z0-9_-]{11})"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

def topic_handler(metadata: dict, logger: Logger, art_download_location: str = os.path.join(os.environ.get('XDG_RUNTIME_DIR', '/tmp'), 'square_thumb.png'), album_art_dl_attempts: int = 3, retry_cooldown: float = 0.1):
    global last_url, last_title, last_artist
    metadata = metadata.copy()
    if metadata['xesam:url'] != last_url:
        if pillow_avalaible:
            video_id = get_youtube_video_id(metadata['xesam:url'])
            image_url = f'https://i.ytimg.com/vi_webp/{video_id}/maxresdefault.webp'
            image_bytes = art_fetcher(image_url, logger, album_art_dl_attempts, retry_cooldown)
            if image_bytes is not None:
                image = Image.open(io.BytesIO(image_bytes))
                l_offset = int(round((image.width - image.height) / 2, 0))
                r_offset = l_offset + image.height
                image = image.crop((l_offset, 0, r_offset, image.height))
                image.save(art_download_location)
                metadata['enhancements:localArtUrl'] = art_download_location
        if 'feat.' in metadata['xesam:title']:
            featured_artists = [i.strip() for i in metadata['xesam:title'].replace('(', '').replace(')', '').split('feat.')[1].split('&')]
            metadata['xesam:artist'] = [*[i.replace('- Topic', '').strip() for i in metadata['xesam:artist']], *featured_artists]
            metadata['xesam:title'] = metadata['xesam:title'].split('(feat.')[0].strip()
        elif 'with' in metadata['xesam:title']:
            featured_artists = [i.strip() for i in metadata['xesam:title'].replace('(', '').replace(')', '').split('with')[1].split('&')]
            metadata['xesam:artist'] = [*[i.replace('- Topic', '').strip() for i in metadata['xesam:artist']], *featured_artists]
            metadata['xesam:title'] = metadata['xesam:title'].split('(with')[0].strip()
        else:
            metadata['xesam:artist'] = [i.replace('- Topic', '').strip() for i in metadata['xesam:artist']]
        last_url = metadata['xesam:url']
        last_title = metadata['xesam:title']
        last_artist = metadata['xesam:artist'].copy()
    else:
        metadata['xesam:artist'] = last_artist
        metadata['xesam:title'] = last_title
        if pillow_avalaible: metadata['enhancements:localArtUrl'] = art_download_location

    return metadata

if __name__ == '__main__':
    logger = Logger(__name__, level=logging.DEBUG)
    metadata = {
        'xesam:title': 'Prototype=DUSK (feat. 巡音ルカ)',
        'xesam:artist': ['ShotenTaro - Topic'],
        'xesam:url': 'https://www.youtube.com/watch?v=5HVocmIJP7Y',
    }
    metadata = topic_handler(metadata, logger)
    print(metadata)
