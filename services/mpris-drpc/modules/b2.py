import os
import time
import requests
from logging import Logger

try:
    import yt_dlp
    ytdl_avalaible = True
except (ImportError, ModuleNotFoundError):
    print('yt-dlp not installed, cannot fill in artist information, resorting to using lower resolutin album art')
    ytdl_avalaible = False

last_art_url = ""
last_title = ""
last_artist = [""]
params = {}

def art_fetcher(url, save_path, logger: Logger, dl_attempts: int = 3, retry_cooldown: float = 0.01):
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

            # Ensure the directory exists
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # Open the file in binary write mode and save the image content
            with open(save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    # Write each chunk of data to the file
                    file.write(chunk)

            logger.info(f"Image successfully downloaded and saved to: {save_path}")
            return

        except requests.exceptions.RequestException as e:
            logger.warning(f"Error during network request: {e}, attempt {i+1} of {dl_attempts}")
        except IOError as e:
            logger.warning(f"Error writing file to disk: {e}, attempt {i+1} of {dl_attempts}")
        except Exception as e:
            logger.warning(f"An unexpected error occurred: {e}, attempt {i+1} of {dl_attempts}")

        time.sleep(retry_cooldown)

def b2_handler(metadata: dict, logger: Logger, art_download_location: str = os.path.join(os.environ.get('XDG_RUNTIME_DIR', '/tmp'), 'nnd_thumb'), album_art_dl_attempts: int = 3, retry_cooldown: float = 0.1):
    global last_title, last_art_url, last_artist
    if not ytdl_avalaible: 
        logger.error('yt-dlp not installed in this environment, if it is installed globally please disable all virtualenvs, this plugin will not execute unless yt-dlp is avalaible')
        return metadata
    metadata = metadata.copy()
    metadata['xesam:title'] = metadata['xesam:title'].strip()
    if metadata['xesam:title'] != last_title:
        with yt_dlp.YoutubeDL() as ydl:
            info = ydl.sanitize_info(ydl.extract_info(metadata['xesam:url'], download=False))
            metadata['xesam:artist'] = [info['uploader']]
            ogp_format = info['thumbnails'][0]
            ogp_url = ogp_format['url']
            art_fetcher(ogp_url, art_download_location, logger, album_art_dl_attempts, retry_cooldown)
            metadata['mpris:artUrl'] = ogp_url
        last_art_url = ogp_url
        last_artist = [info['uploader']]
        last_title = metadata['xesam:title']
        metadata['enhancements:localArtUrl'] = art_download_location
    else:
        metadata['xesam:artist'] = last_artist
        metadata['xesam:artUrl'] = last_art_url
        metadata['enhancements:localArtUrl'] = art_download_location

    return metadata