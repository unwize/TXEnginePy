from abc import ABC


class TagMixin(ABC):
    """
    A mixin that provides a simple interface for storing arbitrary tags.
    """

    def __init__(self, tags: dict[str, float | None] | list[str] = None, **kwargs):
        super().__init__(**kwargs)

        self.tags: dict[str, float] = {}

        if tags is None:
            pass

        # Expand a list into a dict where the value is always None
        elif isinstance(tags, list):
            self.tags = {k: None for k in tags}

        # Type-check the dict and assign it
        elif isinstance(tags, dict):
            self.tags = tags

            for tag, res in self.tags.items():
                if not isinstance(tag, str):
                    raise TypeError()

                if res is not None and not isinstance(res, float):
                    raise TypeError()

        # Boom
        else:
            raise TypeError("Unexpected")

    def get_tag_value(self, tag: str) -> float:
        """
        Look up the given tag and retrieve its associated resistance.

        Args:
            tag: The tag to look up

        Returns: The % resistance to the tag in float form
        """

        if tag not in self.tags or self.tags[tag] is None:
            return 0.0

        return self.tags[tag]

    def has_tag(self, tag: str) -> bool:
        """
        Determine if the object has the given tag

        Returns: True if the tag is found, False otherwise
        """

        return tag in self.tags
