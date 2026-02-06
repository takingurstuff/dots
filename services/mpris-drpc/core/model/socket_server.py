import os
import json
import struct
import logging
import asyncio
from typing import Literal, Any
from collections import defaultdict

from core.constants import log_level

SOCKET_PATH = '/tmp/mpris.sock'
log = logging.getLogger(__name__)
log.setLevel(log_level)

HEADER_SIZE = 4
HEADER_FORMAT = '!I'
INTERVAL = Literal['ON_METADATA', 'ON_STATUS', 'ON_SEEK', 'ON_EVENT']
REQUIRED_PARAMS = ['name', 'interval', 'format_type', 'format']
ALLOWED_PARAMS = ['name', 'interval', 'format_type', 'format']
VALID_INTERVALS = ('ON_METADATA', 'ON_STATUS', 'ON_SEEK', 'ON_EVENT', 'ON_PLAYER')

class Client():
    name: str
    interval: INTERVAL
    format: str | dict[str, str]
    format_type: Literal['str', 'json']
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    listener = None

    def __init__(self, name: str, interval: INTERVAL, output_format_type: Literal['str', 'json'], output_format: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.name = name
        self.interval = interval
        if output_format != 'all':
            match output_format_type:
                case 'json': self._parse_json_format(output_format)
                case 'str': self._parse_str_format(output_format)
        else:
            self.format = output_format
        self.format_type = output_format_type

    def _parse_json_format(self, format_str: str):
        format_dict = json.loads(format_str)
        self.format = format_dict

    def _parse_str_format(self, format_str: str):
        self.format = format_str

    def fill_format(self, metadata: dict[str, Any], **kwargs):
        if kwargs: metadata = metadata.copy(); metadata.update(kwargs)
        metadata = {k.replace(':', '|') : v for k , v in metadata.items()}
        if self.format == 'all':
            return json.dumps(metadata)
        elif self.format_type == 'json':
            ret = self.format.copy()
            for k, v in metadata.items():
                if f'|{k}|' in self.format.values():
                    k = [k for k in self.format.keys() if self.format[k] == v][0]
                    ret[k] = v

            ret = json.dumps(ret)
        else:
            metadata = defaultdict(lambda: "(╯`Д´)╯︵ ┻━┻", metadata)
            ret = self.format.format_map(metadata)
        
        return ret

class SocketServer():
    clients_connected: dict[str, Client] = {}
    client_intervals: dict[INTERVAL, list[str]] = {}
    server: asyncio.Server
    socket_path: str

    def __init__(self, socket_path= SOCKET_PATH):
        if os.path.exists(socket_path):
            os.unlink(socket_path)
        self.socket_path = socket_path

    async def recv_msg(self, reader: asyncio.StreamReader):
        try:
            # Read and parse header
            header = await reader.readexactly(HEADER_SIZE)
            if not header:
                return None
            # unpack the header and read exactly the size specified in header
            msg_size, = struct.unpack(HEADER_FORMAT, header)
            msg_data = await reader.readexactly(msg_size)
            return msg_data
        except (asyncio.IncompleteReadError, ConnectionResetError):
            return None
    
    async def send_msg(self, msg: bytes, writer: asyncio.StreamWriter):
        # get a header
        msg_size = len(msg)
        header = struct.pack(HEADER_FORMAT, msg_size)
        try:
            # send the header containing the size and then the message
            writer.write(header)
            writer.write(msg)
            await writer.drain()
        except (BrokenPipeError, ConnectionResetError) as e:
            log.warning(f"Failed to send message to client: {e}")
            # Re-raise to be handled by the caller
            raise

    async def _setup_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        msg_data = await self.recv_msg(reader)
        if not msg_data:
            log.warning("Client connected but sent no data. Closing connection.")
            writer.close()
            await writer.wait_closed()
            return

        client_requested_params = json.loads(msg_data.decode('utf-8'))

        missing_params = [k for k in REQUIRED_PARAMS if k not in client_requested_params]
        if missing_params:
            err_msg = json.dumps({'Error': f'{missing_params} not found in params'}).encode('utf-8')
            log.warning(f"Client connection rejected. Missing params: {missing_params}")
            await self.send_msg(err_msg, writer)
            return

        if client_requested_params['interval'] not in VALID_INTERVALS:
            err_msg = json.dumps({'Error': f'Invalid Interval: {client_requested_params['interval']}'}).encode('utf-8')
            log.warning(f"Client connection rejected. Invalid interval: {client_requested_params['interval']}")
            await self.send_msg(err_msg, writer)
            return

        ignored_params = [k for k in client_requested_params if k not in ALLOWED_PARAMS]
        if ignored_params:
            warn_msg = json.dumps({'Warning': f'{ignored_params} will be ignored'}).encode('utf-8')
            await self.send_msg(warn_msg, writer)

        name = client_requested_params['name']
        interval = client_requested_params['interval']

        client = Client(name, interval, client_requested_params['format_type'], client_requested_params['format'], reader, writer)
        self.clients_connected[name] = client
        
        if interval not in self.client_intervals:
            self.client_intervals[interval] = []
        self.client_intervals[interval].append(name)
        log.info(f"Client '{name}' connected for interval '{interval}'")

        metadata = self.listener.player_metadata
        msg = client.fill_format(metadata)
        await self.send_msg(msg.encode('utf-8'), writer)

        # Start a background task to listen for commands from the client
        asyncio.create_task(self._listen_for_commands(client))

    async def send_metadata(self, interval: INTERVAL, metadata: dict[str, Any], **kwargs):
        log.debug(f'Metadata send requested for interval: {interval}')
        client_names_to_send_to = self.client_intervals.get(interval, [])
        if not client_names_to_send_to:
            return
        
        for name in client_names_to_send_to[:]: # Iterate over a copy
            client = self.clients_connected.get(name)
            if not client:
                continue
            try:
                msg = client.fill_format(metadata, **kwargs)
                await self.send_msg(msg.encode('utf-8'), client.writer)
            except (BrokenPipeError, ConnectionResetError):
                log.warning(f"Client '{name}' disconnected during send. Removing.")
                self.remove_client(name)

    async def broadcast_msg(self, msg: bytes):
        for name, client in list(self.clients_connected.items()):
            try:
                await self.send_msg(msg, client.writer)
            except (BrokenPipeError, ConnectionResetError):
                log.warning(f"Client '{name}' disconnected during broadcast. Removing.")
                self.remove_client(name)

    async def _listen_for_commands(self, client: Client):
        """Listen for incoming commands from a client in a loop."""
        while True:
            try:
                data = await self.recv_msg(client.reader)

                if data is None:
                    # recv_msg returns None on EOF or connection error
                    log.info(f"Client '{client.name}' connection closed.")
                    self.remove_client(client.name)
                    break

                command = data.decode('utf-8').strip()
                if command == 'disconnect':
                    log.info(f"Client '{client.name}' sent disconnect command. Closing connection.")
                    self.remove_client(client.name)
                    break
                else:
                    log.warning(f"Received unknown command from '{client.name}': {command}")
            except Exception as e:
                log.error(f"Error handling client '{client.name}': {e}. Removing client.")
                self.remove_client(client.name)
                break

    def remove_client(self, name: str):
        client = self.clients_connected.pop(name, None)
        if client:
            if client.interval in self.client_intervals:
                try:
                    self.client_intervals[client.interval].remove(name)
                except ValueError:
                    pass # Already removed
            client.writer.close()

    async def start_server(self, listener):
        self.listener = listener
        log.info("Unix Domain Socket Server Starting Up at %s", self.socket_path)
        self.server = await asyncio.start_unix_server(self._setup_client, self.socket_path)

    async def stop_server(self):
        log.info("Unix Domain Socket Server Shutting Down")
        await self.broadcast_msg(json.dumps({'Warning': 'Server is shutting down'}).encode('utf-8'))
        for client in self.clients_connected.values():
            client.writer.close()
        self.server.close()
        await self.server.wait_closed()
        if os.path.exists(self.socket_path): os.unlink(self.socket_path)