import signal
import asyncio
import logging
from dbus_next import BusType
from dbus_next.aio.message_bus import MessageBus

from core.constants import log_level
from core.model.config import Config
from core.model.dbus import DbusListener
from core.model.socket_server import SocketServer

log = logging.getLogger(__name__)


async def discover_initial_players(interface, listener):
    """Finds and connects to players already running on the bus."""
    names = await interface.call_list_names()
    mpris_names = [
        n
        for n in names
        if n.startswith("org.mpris.MediaPlayer2") and "playerctld" not in n
    ]

    if mpris_names:
        log.info(f"Found existing media players: {mpris_names}")
        await listener.connect_bulk(mpris_names)


async def run_application():
    config = Config.from_config()
    stop_event = asyncio.Event()

    # 1. Setup D-Bus
    bus = await MessageBus(bus_type=BusType.SESSION).connect()

    try:
        # 2. Setup Server and Listener
        server = SocketServer()
        listener = DbusListener(config, bus, server)
        await server.start_server(listener)

        # 3. Setup MPRIS Monitoring
        introspection = await bus.introspect(
            "org.freedesktop.DBus", "/org/freedesktop/DBus"
        )
        obj = bus.get_proxy_object(
            "org.freedesktop.DBus", "/org/freedesktop/DBus", introspection
        )
        dbus_interface = obj.get_interface("org.freedesktop.DBus")

        # Connect to existing players
        await discover_initial_players(dbus_interface, listener)

        # Listen for new players
        dbus_interface.on_name_owner_changed(
            lambda name, old, new: listener.handle_connection(name, old, new, False)
        )

        log.info("Application started. Global listener active.")

        # 4. Handle Termination Signals gracefully
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_event.set)

        # Wait until a signal is received
        await stop_event.wait()

    except Exception:
        log.exception("Fatal error during runtime")
        raise
    finally:
        log.info("Shutting down...")
        # Order matters: Stop server -> Disconnect Listeners -> Disconnect Bus
        if server:
            await server.stop_server()
        if listener:
            listener.disconnect_all()
        if bus:
            bus.disconnect()
        log.info("Shutdown complete.")


if __name__ == "__main__":
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    try:
        asyncio.run(run_application())
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
