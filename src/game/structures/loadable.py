from typing import Callable


class LoadableMixin:
    """
    An interface for classes that need to define logic for building an instance
    from JSON.
    """

    LOADER_KEY: str = "loader"
    ATTR_KEY: str = "from_json"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def get_loader(cls) -> Callable:
        """
        Fetch and return the JSON loader function for this class as stored in
        the cache.

        Returns: A callable that can be used to translate a JSON object into
        an object of this type.

        Raises:
            KeyError:
        """
        from game.cache import from_cache

        return from_cache([cls.LOADER_KEY, cls.__name__, cls.ATTR_KEY])
