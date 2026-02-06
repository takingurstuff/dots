import time
import logging
from dbus_next.aio import MessageBus

from core.model.player import Player
from core.constants import log_level
from core.model.config import Config
from core.model.socket_server import SocketServer

SPECiAL_PLAYERS = ['playerctld']

log = logging.getLogger(__name__)
log.setLevel(log_level)

class DbusListener():
    bus: MessageBus
    server: SocketServer
    players_connected: dict[str, Player] = {}
    config: Config

    def __init__(self, config: Config, bus: MessageBus, server: SocketServer):
        self.bus = bus
        self.server = server
        self.config = config

    def disconnect_player(self, player_name: str):
        if player_name in self.players_connected:
            log.info(f'Player {player_name} disconnected, removing its entry')
            player = self.players_connected[player_name]
            obj = player.interface
            interface_properties = obj.get_interface('org.freedesktop.DBus.Properties')
            interface_seek = obj.get_interface('org.mpris.MediaPlayer2.Player')
            interface_properties.off_properties_changed(player.on_update)
            interface_seek.off_seeked(player.on_seek)
            del self.players_connected[player_name]
    
    def disconnect_all(self):
        for name in self.players_connected.copy():
            self.disconnect_player(name)

    async def handle_connection(self, name: str, old_owner: str, new_owner: str, existing_conn: bool):
        if not name.startswith('org.mpris.MediaPlayer2') or any([i in name for i in SPECiAL_PLAYERS]):
            return
        player_name = name.replace('org.mpris.MediaPlayer2.', '')
        if new_owner:
            log.info(f'Player {player_name} just connected, setting up listener')
        else:
            self.disconnect_player(player_name)
            metadata = self.player_metadata
            await self.server.send_metadata('ON_EVENT', metadata)
            await self.server.send_metadata('ON_SEEK', metadata)
            await self.server.send_metadata('ON_METADATA', metadata)
            await self.server.send_metadata('ON_STATUS', metadata)
            return

        log.debug('Initializing Interface')
        introspection = await self.bus.introspect(name, '/org/mpris/MediaPlayer2')
        obj = self.bus.get_proxy_object(name, '/org/mpris/MediaPlayer2', introspection)
        interface_properties = obj.get_interface('org.freedesktop.DBus.Properties')
        interface_seek = obj.get_interface('org.mpris.MediaPlayer2.Player')

        event_cb = lambda metadata, **kwargs: self.server.send_metadata('ON_EVENT', metadata, **kwargs)
        seek_cb = lambda metadata, **kwargs: self.server.send_metadata('ON_SEEK', metadata, **kwargs)
        metadata_cb = lambda metadata, **kwargs: self.server.send_metadata('ON_METADATA', metadata, **kwargs)
        status_cb = lambda metadata, **kwargs: self.server.send_metadata('ON_STATUS', metadata, **kwargs)

        player = Player(self.config, player_name, obj, event_cb, seek_cb, metadata_cb, status_cb)
        interface_properties.on_properties_changed(player.on_update)
        interface_seek.on_seeked(player.on_seek)
        if existing_conn:
            await player.force_update()
            await player.on_seek(1)
        self.players_connected[player_name] = player

    async def connect_existing(self, service_name: str):
        await self.handle_connection(service_name, '', service_name, True)

    async def connect_bulk(self, services: list[str]):
        for service in services:
            await self.connect_existing(service)

    @property
    def active_player(self):
        if not self.players_connected:
            return None, None
        # Sort by active status (True first) and then by most recent activity
        return sorted(self.players_connected.items(), key=lambda item: (item[1].active, item[1].last_active), reverse=True)[0]
    
    @property
    def player_metadata(self):
        _, player = self.active_player
        if player:
            metadata = player.metadata.copy()
            metadata.update(player.extra_properties)
            return metadata
        else:
            return {}