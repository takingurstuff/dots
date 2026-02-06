import os
import re
import time
import base64
import requests
from logging import Logger

try:
    import yt_dlp
    ytdl_avalaible = True
except (ImportError, ModuleNotFoundError):
    print('yt-dlp not installed, cannot perform HQ image retrival for certain sites')
    ytdl_avalaible = False

last_art_url = ""

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

def decode_base64(base64_str: str, save_path: str, logger: Logger):
    clean_base64 = base64_str.split('base64,')[-1].strip()
    image_bytes = base64.b64decode(clean_base64)
    with open(save_path, 'wb') as f:
        f.write(image_bytes)
    logger.debug('Image Saved')

def localize(metadata: dict, logger: Logger, art_download_location: str = os.path.join(os.environ.get('XDG_RUNTIME_DIR', '/tmp'), 'general_thumb'), album_art_dl_attempts: int = 3, retry_cooldown: float = 0.1):
    global last_art_url
    metadata = metadata.copy()
    art_url = metadata.get('mpris:artUrl')
    if not art_url: return metadata
    if 'enhancements:localArtUrl' in metadata: return metadata

    if art_url != last_art_url:
        if art_url.startswith('data:image/'): decode_base64(art_url, art_download_location, logger)
        elif art_url.startswith('http'): art_fetcher(art_url, art_download_location, logger, album_art_dl_attempts, retry_cooldown)
        elif art_url.startswith('file:///'): art_download_location = art_url.replace('file://', '')
        elif os.path.exists(art_url): art_download_location = art_url
        metadata['enhancements:localArtUrl'] = art_download_location
        last_art_url = art_url
    else:
        if art_url.startswith('file:///'): art_download_location = art_url.replace('file://', '')
        elif os.path.exists(art_url): art_download_location = art_url
        metadata['enhancements:localArtUrl'] = art_download_location
    return metadata