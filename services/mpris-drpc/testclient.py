import os
import sys
import json
import struct
import logging
import asyncio
import argparse

# --- Configuration ---
# This should match the socket path in your server script.
SOCKET_PATH = '/tmp/mpris.sock'
HEADER_SIZE = 4
HEADER_FORMAT = '!I' # Use the same format as the server

# --- Logger Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

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

async def main_client(args):
    """
    The main function for the client. Connects, configures, and listens for messages.
    """
    log.info(f"Attempting to connect to server at {SOCKET_PATH}...")
    
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
        'interval': args.interval,
        'format_type': args.format_type,
        'format': args.format
    }
    
    log.info(f"Sending configuration: {client_params}")
    
    try:
        await send_msg(writer, json.dumps(client_params).encode('utf-8'))
    except Exception:
        log.error("Could not send initial configuration. Exiting.")
        writer.close()
        await writer.wait_closed()
        return

    # --- Listen for messages from the server ---
    log.info("Connection successful. Listening for messages from the server...")
    log.info("Press Ctrl+C to disconnect.")
    
    try:
        while True:
            response = await recv_msg(reader)
            if response is None:
                # Server closed the connection
                break
            
            # Print the received message from the server
            print(f"\n--- Server Message ---\n{response}\n----------------------")

    except asyncio.CancelledError:
        log.info("Disconnecting as requested by user. Sending 'disconnect' command.")
        try:
            await send_msg(writer, b'disconnect')
        except (BrokenPipeError, ConnectionResetError):
            log.warning("Could not send disconnect command, server may have already closed connection.")
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}")
    # finally:
    #     log.info("Disconnecting as requested by user. Sending 'disconnect' command.")
    #     try:
    #         # Inform the server we are disconnecting gracefully.
    #         await send_msg(writer, b'disconnect')
    #         log.info("Closing connection.")
    #         writer.close()
    #         await writer.wait_closed()

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
        type=str,
        required=True,
        choices=['ON_METADATA', 'ON_STATUS', 'ON_SEEK', 'ON_EVENT'],
        help="The event interval to subscribe to."
    )
    parser.add_argument(
        '--format-type',
        type=str,
        required=True,
        choices=['str', 'json'],
        help="The type of format string to use ('str' or 'json')."
    )
    parser.add_argument(
        '--format',
        type=str,
        required=True,
        help="The format string for the output.\n"
             "For 'str' type, use placeholders like '{artist} - {title}'.\n"
             "For 'json' type, provide a JSON string like '{\\\"artist\\\": \\\"{artist}\\\", \\\"title\\\": \\\"{title}\\\"}'."
    )

    args = parser.parse_args()
    
    # Validate that the format string is valid JSON if the type is 'json'
    if args.format_type == 'json':
        try:
            json.loads(args.format)
        except json.JSONDecodeError:
            log.error("Error: The provided format string is not valid JSON.")
            sys.exit(1)

    try:
        asyncio.run(main_client(args))
    except Exception as e:
        log.error(f"Client stopped due to an error: {e}")
