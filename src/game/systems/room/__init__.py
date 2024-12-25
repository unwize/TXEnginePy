"""
Host of the room_manager package-level variable
"""

from game.systems.room.room import Room
from game.systems.room.room_manager import RoomManager


room_manager = RoomManager()

__all__ = ["Room", "room_manager"]
