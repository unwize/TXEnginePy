from game.cache import cached


class LoadableMixin:
    """An interface for classes that need to define logic for building an instance from JSON"""

    LOADER_KEY: str = 'loader'
    ATTR_KEY: str = "from_json"

    def __init__(self):
        if self.ATTR_KEY not in self.__dict__:
            raise RuntimeError(f"{self.__class__.__name__} is Loadable but does not implement {self.ATTR_KEY}!")

    @cached(LOADER_KEY, "LoadableMixin")
    def from_json(self, json: dict[str, any]) -> any:
        raise NotImplementedError()
