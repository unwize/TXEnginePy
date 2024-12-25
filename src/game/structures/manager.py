import typing
from abc import ABC

from loguru import logger

import game.cache as cache


class Manager(ABC):
    """
    An interface for defining manager behavior. A manager must:
    - Define loading behavior
    - Define saving behavior
    typically for an entire system.
    """

    def __init__(self):
        self.name = self.__class__.__name__
        self._manifest: dict = {}

        if "managers" not in cache.get_cache():
            logger.debug("Creating managers cache...")
            cache.get_cache()["managers"] = {}

        if self.name not in cache.get_cache()["managers"]:
            logger.debug(f"[{self.name}] Registering manager with cache...")
            cache.get_cache()["managers"][self.name] = self

        self.command_handlers: dict[str, typing.Callable] = {"list": self._command_list}

    def load(self) -> None:
        raise NotImplementedError

    def save(self) -> None:
        raise NotImplementedError

    def is_id(self, id: any) -> bool:
        """
        Check if a given ID has already been taken
        """

        return id in self._manifest

    def _command_list(self, fields: str) -> list[str]:
        """
        Return a list of strings where each line corresponds to the selected fields of
        a specific object in the manifest.

        For example, 'list name id' would return
            'element0.name element0.id
             element1.name element1.id
             ...
             elementN.name elementN.id
             '
        """

        parts = fields.split(" ")
        buffer = []

        if len(parts) == 0:
            return buffer

        for obj in self._manifest.values():
            sub_buffer = ""

            for field in parts:
                if not hasattr(obj, field):
                    raise AttributeError(f"Object of type {type(obj)} has no attribute {field}!")

                sub_buffer += str(getattr(obj, field)) + " "

            buffer.append(sub_buffer)

        return buffer

    def handle_command(self, command: str) -> str:
        """
        Dispatch the 1th-nth split element down to the appropriate command handler
        """
        parts = command.split(" ")

        if parts[0] not in self.command_handlers:
            return f"Unknown command: {parts[0]}"

        return self.command_handlers[parts[0]](" ".join(parts[1:]))
