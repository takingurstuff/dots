import time
import logging
import asyncio
from typing import Coroutine
from dbus_next import Variant
from typing import Literal, Callable, Any
from dbus_next.aio.proxy_object import ProxyObject

from core.constants import log_level
from core.model.config import Config
from core.metadata_parser import metadata_process

CALLBACK_TYPE = Callable[[dict[str, Any], Any], Coroutine[Any, Any, None]] | None

log = logging.getLogger(__name__)
log.setLevel(log_level)

class Player:
    def __init__(self, config: Config, player_name: str, player_dbus_proxy: ProxyObject, event_callback: CALLBACK_TYPE, seek_callback: CALLBACK_TYPE, metadata_callback: CALLBACK_TYPE, status_callback: CALLBACK_TYPE):
        self.interface = player_dbus_proxy
        self.name = player_name
        self.active = True
        self.last_active = 0
        self.media_start = 0
        self.existing_time = 0
        self.metadata: dict[str, str | int] = {}
        self.status: Literal['Playing', 'Paused', 'Stopped'] = 'Stopped'
        self.lyric = ""
        self.event_callback: CALLBACK_TYPE = event_callback
        self.seek_callback: CALLBACK_TYPE = seek_callback
        self.metadata_callback: CALLBACK_TYPE = metadata_callback
        self.status_callback: CALLBACK_TYPE = status_callback
        self.config: Config = config
        self.metadata_lock = asyncio.Lock()
        self.last_raw_metadata = {}
    
    @property
    def extra_properties(self):
        return {'tracking:startTime': self.media_start, 'tracking:existingTime': self.existing_time, 'tracking:status': self.status}

    def _pause(self):
        if self.status == 'Paused':
            return
        cur = time.time()
        self.active = False
        self.status = 'Paused'
        self.existing_time += cur - self.media_start
        self.media_start = cur
        self.last_active = cur

    def _play(self):
        if self.status == 'Playing':
            return
        self.status = 'Playing'
        cur = time.time()
        self.paused = False
        self.media_start = cur
        self.active = True

    def _stop(self):
        cur = time.time()
        self.status = 'Stopped'
        self.active = False
        self.last_active = cur
        self.existing_time = 0
        self.metadata: dict[str, str | int] = {}

    async def on_seek(self, position_usec: int):
        interface = self.interface.get_interface('org.mpris.MediaPlayer2.Player')
        position = float(await interface.get_position()) / 1_000_000
        self.existing_time = position
        self.media_start = time.time()
        metadata = self.metadata.copy()
        metadata.update(self.extra_properties)
        if self.seek_callback:
            await self.seek_callback(metadata)
        if self.event_callback:
            await self.event_callback(metadata)

    async def set_metadata(self, metadata: dict[str, Variant]):
        async with self.metadata_lock:
            metadata = {k: v.value for k, v in metadata.items()}
            if 'mpris:length' in metadata: metadata['mpris:length'] /= 1_000_000
            keys_to_compare = ['xesam:title', 'xesam:url', 'mpris:artUrl', 'xesam:artist']
            if all([metadata.get(key, '1') == self.last_raw_metadata.get(key, '2') for key in keys_to_compare]):
                log.debug(f"[{self.name}] Redundant metadata signal received. Skipping processing.")
                if metadata.get('mpris:length', 1) != self.last_raw_metadata.get('mpris:length', 1):
                    self.metadata['mpris:length'] = metadata['mpris:length']
                    if self.metadata_callback:
                        await self.metadata_callback(self.metadata)
                    if self.event_callback:
                        await self.event_callback(self.metadata)
                return
            self.last_raw_metadata = metadata.copy()
            metadata = metadata_process(self.config, metadata)
            self.metadata = metadata.copy()
            metadata.update(self.extra_properties)
            if self.metadata_callback:
                await self.metadata_callback(metadata)
            if self.event_callback:
                await self.event_callback(metadata)

    async def update_status(self, status: Literal['Playing', 'Paused', 'Stopped']):
        match status:
            case 'Playing': self._play()
            case 'Paused': self._pause()
            case 'Stopped': self._stop()
            case _: raise ValueError('Unexpected Status')
        metadata = self.metadata.copy()
        metadata.update(self.extra_properties)
        if self.status_callback:
            await self.status_callback(metadata)
        if self.event_callback:
            await self.event_callback(metadata)

    async def on_update(self, interface_name, changed_properties: dict[str, Variant | Any], invalidated_properties):
        changed_properties = {k: (v.value if isinstance(v, Variant) else v) for k, v in changed_properties.items()}
        if 'PlaybackStatus' in changed_properties:
            status = changed_properties['PlaybackStatus']
            await self.update_status(status)
        if 'Metadata' in changed_properties:
            log.debug(f"[{self.name}] Metadata updated.")
            await self.set_metadata(changed_properties['Metadata'])
            await self.on_seek(1)

    async def force_update(self):
        interface = self.interface.get_interface('org.mpris.MediaPlayer2.Player')
        metadata = await interface.get_metadata()
        status = await interface.get_playback_status()
        metadata_dict = {'Metadata': metadata, 'PlaybackStatus': status}
        await self.on_update({}, metadata_dict, {})
        await self.on_seek(1)