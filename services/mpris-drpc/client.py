import os
import sys
import json
import time
import html
import struct
import logging
import asyncio
import argparse

# --- Configuration ---
# This should match the socket path in your server script.
SOCKET_PATH = '/tmp/mpris.sock'
HEADER_SIZE = 4
HEADER_FORMAT = '!I' # Use the same format as the server
PLAY_ICON_PATH="/home/talent/.config/eww/icons/play.svg"
PAUSE_ICON_PATH="/home/talent/.config/eww/icons/pause.svg"
STOP_ICON_PATH="/home/talent/.config/eww/icons/stop.svg"
DEF_ALBUM_ART_PATH="/home/talent/.config/eww/icons/transparent_image.png"
PLAY_ICON="▶"
PAUSE_ICON="⏸"
STOP_ICON="⏹"


# Temporary global metadata storage
metadata: dict = {}

# --- Logger Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def seconds_to_hms(seconds):
    """
    Converts a duration in seconds to a string in the format HH:MM:SS.

    Args:
        seconds: An integer representing the duration in seconds.

    Returns:
        A string in the format HH:MM:SS.
    """
    if not isinstance(seconds, int) or seconds < 0:
        raise ValueError("Input must be a non-negative integer representing seconds.")

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60

    return f"{hours:02}:{minutes:02}:{remaining_seconds:02}" if hours > 0 else f"{minutes:02}:{remaining_seconds:02}"

async def recv_msg(reader: asyncio.StreamReader) -> str | None:
    """
    Receives a message prefixed with a size header from the socket.
    
    Args:
        reader: The asyncio StreamReader to read from.

    Returns:
        The decoded message as a string, or None if the connection is closed.
    """
    try:
        # Read the header to determine the incoming message size.
        header = await reader.readexactly(HEADER_SIZE)
        if not header:
            return None
        
        # Unpack the header to get the message size.
        msg_size, = struct.unpack(HEADER_FORMAT, header)
        
        # Read the exact size of the message payload.
        msg_data = await reader.readexactly(msg_size)
        return msg_data.decode('utf-8')
    except (asyncio.IncompleteReadError, ConnectionResetError):
        log.info("Connection to the server was lost.")
        return None
    except Exception as e:
        log.error(f"An unexpected error occurred while receiving a message: {e}")
        return None

async def send_msg(writer: asyncio.StreamWriter, msg: bytes):
    """
    Sends a message prefixed with a size header to the socket.

    Args:
        writer: The asyncio StreamWriter to write to.
        msg: The message payload as bytes.
    """
    try:
        # Pack the message size into a header.
        header = struct.pack(HEADER_FORMAT, len(msg))
        
        # Write the header followed by the message.
        writer.write(header)
        writer.write(msg)
        await writer.drain()
    except (BrokenPipeError, ConnectionResetError):
        log.error("Failed to send message: Connection lost.")
        raise # Re-raise to be handled by the main loop

def remove_bidi_characters(s: str) -> str:
    """Removes common bidirectional Unicode control characters."""
    # List of common bidi control characters
    bidi_chars = [
        '\u200E',  # Left-to-Right Mark (LRM)
        '\u200F',  # Right-to-Left Mark (RLM)
        '\u202A',  # Left-to-Right Embedding (LRE)
        '\u202B',  # Right-to-Left Embedding (RLE)
        '\u202C',  # Pop Directional Formatting (PDF)
        '\u202D',  # Left-to-Right Override (LRO)
        '\u202E',  # Right-to-Left Override (RLO)
    ]
    for char in bidi_chars:
        s = s.replace(char, '')
    return s


async def metadata_loop(reader: asyncio.StreamReader, for_panel: bool):
    global metadata
    while True:
        log.info('new server message')
        response = await recv_msg(reader)
        if response is None:
            # Server closed the connection
            break
        metadata = json.loads(response)
        # p_metadata = metadata.copy()
        # del p_metadata['sesam|artUrl']
        # print(json.dumps(metadata), file=sys.stderr)
        if metadata:
            metadata['tracking|readableLength'] = seconds_to_hms(int(round(float(metadata.get('mpris|length', 1.0)), 0)))
            metadata['xesam|title'] = html.escape(metadata.get('xesam|title', 'None')) if for_panel else metadata.get('xesam|title', 'None') 
            metadata['xesam|artist'] = [f"{remove_bidi_characters(html.escape(i) if for_panel else i)}\u200E" for i in metadata.get('xesam|artist', ['None'])]
            print(metadata['xesam|artist'])

def fill_format(for_panel: bool):
    global metadata
    if not metadata or metadata.get('xesam|title') == "None":
        return "No Player Found. " if not for_panel else json.dumps({
            'status': STOP_ICON_PATH,
            'title': 'No Players Found',
            'artist': "None",
            'arturl': "",
            'prog': 0.0,
            'pos': "00:00",
            'dur': "00:00",
        })
    _metadata = metadata.copy()
    artist_list = _metadata.get('xesam|artist')
    artist_str = f"{artist_list[0]} (feat. {', '.join(artist_list[1:])})" if len(artist_list) > 1 else artist_list[0] if len(artist_list) == 1 else 'Unknown Artist'
    # artist_str = ', '.join(artist_list) if len(artist_list) > 0 else 'Unknown Artist'

    position = (time.time() - float(_metadata.get('tracking|startTime', 0.0)) + float(_metadata.get('tracking|existingTime', 0.0))) if _metadata.get('tracking|status') == 'Playing' else _metadata.get('tracking|existingTime', 0.0)
    readable_position = seconds_to_hms(int(round(position, 0)))
    pct = position / float(_metadata.get('mpris|length', 1.0)) * 100

    if for_panel:
        match _metadata.get('tracking|status'):
            case 'Playing':
                icon = PLAY_ICON_PATH
            case 'Paused':
                icon = PAUSE_ICON_PATH
            case 'Stopped':
                icon = STOP_ICON_PATH
            case _:
                icon = STOP_ICON_PATH
        if "enhancements|localArtUrl" in _metadata:
            arturl = _metadata["enhancements|localArtUrl"]
        elif 'mpris|artUrl' in _metadata:
            arturl = _metadata['mpris|artUrl']
        else:
            arturl = DEF_ALBUM_ART_PATH
        ret = json.dumps({
            'status': icon,
            'title': _metadata.get('xesam|title', "Unknown Title"),
            'artist': artist_str,
            'arturl': arturl,
            'prog': pct,
            'pos': readable_position,
            'dur': _metadata.get('tracking|readableLength', "00:00"),
        })
    else:
        match _metadata.get('tracking|status'):
            case 'Playing':
                icon = PLAY_ICON
            case 'Paused':
                icon = PAUSE_ICON
            case 'Stopped':
                icon = STOP_ICON
            case _:
                icon = STOP_ICON
        ret = f"{icon} {_metadata.get('xesam|title', 'Unknown Title')} - {artist_str} - {readable_position} : {_metadata.get('tracking|readableLength', '00:00')}"
    return ret

async def print_metadata(interval: float, for_panel: bool):
    while True:
        print(fill_format(for_panel), flush=True)
        await asyncio.sleep(interval)

async def main_client(args):
    """
    The main function for the client. Connects, configures, and listens for messages.
    """
    # log.info(f"Attempting to connect to server at {SOCKET_PATH}...")
    
    if not os.path.exists(SOCKET_PATH):
        log.error(f"Error: Unix socket not found at {SOCKET_PATH}. Is the server running?")
        sys.exit(1)

    try:
        reader, writer = await asyncio.open_unix_connection(SOCKET_PATH)
    except Exception as e:
        log.error(f"Failed to connect to the socket: {e}")
        sys.exit(1)

    # --- Prepare and send the initial configuration message ---
    client_params = {
        'name': args.name,
        'interval': 'ON_EVENT',
        'format_type': 'json',
        'format': 'all'
    }
    
    # log.info(f"Sending configuration: {client_params}")
    
    try:
        await send_msg(writer, json.dumps(client_params).encode('utf-8'))
    except Exception:
        log.error("Could not send initial configuration. Exiting.")
        writer.close()
        await writer.wait_closed()
        return

    # --- Listen for messages from the server ---
    # log.info("Connection successful. Listening for messages from the server...")
    # log.info("Press Ctrl+C to disconnect.")
    
    try:
        # while True:
        #     response = await recv_msg(reader)
        #     if response is None:
        #         # Server closed the connection
        #         break
            
        #     # Print the received message from the server
        #     print(f"\n--- Server Message ---\n{response}\n----------------------")
        asyncio.create_task(metadata_loop(reader, args.for_panel))
        asyncio.create_task(print_metadata(args.interval, args.for_panel))

        await asyncio.Future()

    except asyncio.CancelledError:
        log.info("Disconnecting as requested by user. Sending 'disconnect' command.")
        try:
            await send_msg(writer, b'disconnect')
        except (BrokenPipeError, ConnectionResetError):
            log.warning("Could not send disconnect command, server may have already closed connection.")
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A simple command-line client for the MPRIS socket server.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '--name',
        type=str,
        required=True,
        help="A unique name for this client instance."
    )
    parser.add_argument(
        '--interval',
        type=float,
        required=True,
        help="The freqnecy to try to print metadata in"
    )
    parser.add_argument(
        '--for-panel',
        type=bool,
        help="Setting this flag will cause the program to evaluate format as json instead of a string",
    )

    args = parser.parse_args()
    
    try:
        asyncio.run(main_client(args))
    except Exception as e:
        log.error(f"Client stopped due to an error: {e}")
