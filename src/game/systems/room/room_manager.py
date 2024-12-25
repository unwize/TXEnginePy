from loguru import logger

from game.structures import manager as manager
from game.structures.loadable_factory import LoadableFactory
from game.systems.room import room as room
from game.systems.room.action.actions import Action
from game.util.asset_utils import get_asset


class RoomManager(manager.Manager):
    """
    A Manager class that hosts a master list of all Room object.
    """

    ROOM_ASSET_PATH = "rooms"

    def __init__(self):
        super().__init__()

        self.rooms: dict[int, room.Room] = {}
        self.visited_rooms: set[int] = set()
        self._manifest: dict[int, room.Room] = self.rooms
        self._default_actions: list[dict[str, any]] = []  # A set of Actions that are added to every Room by default

    def register_room(self, room_object: room.Room, room_id_override: int = None) -> None:
        """
        Register a Room object with the RoomManager

        Args:
            room_object (int): The room to register
            room_id_override (int): An optional value that overrides the room_object's ID

        Returns: None
        """
        if room_object.id in self.rooms or room_id_override in self.rooms:
            raise ValueError(f"Cannot register duplicate room_id for room:{room_object.id}!")

        self.rooms[room_id_override or room_object.id] = room_object

    def get_room(self, room_id: int) -> room.Room:
        """
        Return a reference to the desired room.

        Args:
            room_id (int): The ID of the room the retrieve

        Returns: The desired Room
        """

        if room_id not in self.rooms:
            raise ValueError(f"Cannot retrieve Room:{room_id}! No such Room exists!")

        return self.rooms[room_id]

    def visit_room(self, r: int | room.Room) -> None:
        """
        Sets a room as 'visited' by the RoomManager

        Args:
            r (int | Room): The room or room id to add.

        Returns: None
        """

        if type(r) is int:
            self.visited_rooms.add(r)
        elif type(r) is room.Room:
            self.visited_rooms.add(r.id)
        else:
            raise TypeError(f"Expected type int or Room! Got {type(r)} instead.")

    def is_visited(self, room_id: int) -> bool:
        """
        Returns True if the room_id has been visited before
        """

        return room_id in self.visited_rooms

    def get_name(self, room_id: int) -> str:
        """
        Retrieve the name of the Room with id == room_id

        Args:
            room_id (int): the ID of the room to retrieve

        Returns: The name of the room
        """

        if type(room_id) is not int:
            raise TypeError(f"room_id must be an int! Got object of type {type(room_id)} instead.")

        if room_id not in self.rooms:
            raise ValueError(f"No such room with room_id:{room_id}!")

        return self.rooms[room_id].name

    def load(self) -> None:
        """
        Load rooms from disk
        """

        raw_asset: dict[str, any] = get_asset(self.ROOM_ASSET_PATH)

        # Load default actions
        logger.info("Loading default actions...")
        self._default_actions = raw_asset["config"]["default_actions"]

        # Load rooms
        for raw_room in raw_asset["content"]:
            r = LoadableFactory.get(raw_room)

            if not isinstance(r, room.Room):
                raise TypeError(f"Expected object of type Room, got type {type(r)} instead!")

            self.register_room(r)

    def save(self) -> None:
        """
        Save room metadata to disk
        """
        pass

    def get_default_actions(self) -> list[Action]:
        """
        Get deep-copies of the default Room actions.
        """

        return [LoadableFactory.get(raw_action) for raw_action in self._default_actions]
