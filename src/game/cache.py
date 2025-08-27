"""
A utility python file that hosts a global cache, global config, and useful
accessor/setter methods
"""

import uuid
from typing import Callable
from loguru import logger

config: dict[str, any] = None
cache: dict[str, any] = {}  # For objects that should have common access
storage: dict[str, any] = {}  # For objects not intended to have general access


def decode_path(path: list[str] | str) -> list[str]:
    """
    Decodes a path and returns a list[str] via dot-notation.
    """

    if type(path) is not list and type(path) is not str:
        raise TypeError(f"Unexpected cache path type: {type(path)}! " f"Allowed types are list[str] and str!")
    elif type(path) is list:
        for key in path:
            if type(key) is not str:
                raise TypeError(f"Unexpected type within a listed cache path: " f"{type(key)}! Allowed types are str")
        return path
    elif type(path) is str:
        return path.split(".")


def from_cache(path: list[str] | str) -> any:
    """
    A universal cache-retrieval function.

    Elements cached can be retrieved via their dict-path using a list of keys or
    string dot-notation.

    args:
        path: A list of nested dict keys or a string of dot notation

    returns:
        The element in the cache stored at the lowest level of the dict-path
    """

    true_path = decode_path(path)

    depth = get_cache()

    try:
        for key in true_path[:-1]:  # Skip last key in path
            if key not in depth:
                raise KeyError(f"Invalid cache path key: {key}")
            if type(depth[key]) is not dict:
                raise TypeError(f"Expected key {key}'s value to be of type dict! " f"Got {type(depth[key])} instead.")

            depth = depth[key]

        return depth[true_path[-1]]
    except KeyError as ke:
        logger.warning(f"Caught a key-error while searching cache: {ke}")
        return None


def cache_element(path: list[str] | str, element: any) -> None:
    """
    Universal logic for caching an element in the cache. Using a collection of
    strings or a dot-notated path string, cache an object along a dict-path of
    'path'.
    """

    true_path = decode_path(path)

    depth = get_cache()
    for key in true_path[:-1]:
        if key in depth and type(depth[key]) is not dict:
            raise KeyError("Cannot create path dict in cache! A collision was detected.")

        if key in depth and type(depth[key] is dict):
            pass

        else:
            depth[key] = {}

        depth = depth[key]

    depth[true_path[-1]] = element


def get_cache() -> dict:
    """
    Retrieve a reference to the cache
    """
    global cache
    return cache


def set_config(cfg: dict) -> None:
    """
    Set the config dict
    """
    global config
    config = cfg


def get_config() -> dict:
    """
    Retrieve a reference to the config dict
    """
    global config
    return config


def get_loader(cls: type | str) -> Callable:
    """
    A convenience wrapper that fetches loader functions from the cache for a
    given class.

    args:
        cls:
            Either a type or str representation of a type whose loader to fetch

    returns: A reference to the requested loader function
    """
    from game.structures.loadable import LoadableMixin

    key = str(cls)
    loader_base_path = [LoadableMixin.LOADER_KEY]
    loader_full_path = loader_base_path + [key, LoadableMixin.ATTR_KEY]

    if key in from_cache(loader_base_path):
        try:
            return from_cache(loader_full_path)
        except KeyError as ke:
            logger.error(f"Failed to locate loader for {str(cls)}")
            raise ke
    else:
        raise KeyError(
            f"No loader found for class {key}! Available loaders:" f"\n{' '.join(list(get_cache()['loader'].keys()))}"
        )


def delete_element(path: str | list[str], delete_branch: bool = False, force: bool = False):
    """
    Delete an element from the cache

    If 'delete_branch' is True, attempt to delete the entire branch of sub-dicts
    that store the element. If other cached elements depend on those sub-dicts,
    they will not be removed. If 'force' is True, all sub-dicts and all of their
    contents will be removed.

    args:
        path:
            The path in the cache to delete. By default, only the final value
            (ie the leaf of the path) is removed.
        delete_branch:
            If true, delete all the sub-dicts down to the root node.
        force:
            If true, delete_branch will ignore any dependent branches and still
            delete the entire sub-dict tree.
    """

    true_path: list[str] = decode_path(path)

    # Can the entire branch be deleted without breaking other cache values
    is_clean = True

    depth = get_cache()

    for key in true_path[:-1]:  # For each key except the last one
        if key in depth:  # Check that the next sub-dict exists
            depth = depth[key]  # Move to next sub-dict
            if not isinstance(depth, dict):  # Check that it's actually a dict
                logger.warning(f"Failed to delete {path} from cache! " f"Invalid path. Key {key} is not a dict!")
                break  # Stop executing logic

            # If there's more than one element in the sub-dict, it cannot
            # possibly be cleanly deleted
            if len(depth) > 1:
                is_clean = False

        else:
            logger.warning(f"Failed to delete {path} from cache! Invalid path. " f"Missing key at {key}.")
            break

    # Handle deleting an entire branch of sub-dicts
    if delete_branch:
        if is_clean or force:  # If the branch is clean or force is True
            depth = get_cache()

            # Delete connection between root of the cache and shallowest leaf
            del depth[true_path[0]]
        else:
            logger.warning(f"Failed to delete {path} from cache! " f"Path is not clean and Force == False")

    # Handle standard deletion logic
    else:
        # Check if the final key exists in the final sub-dict
        if true_path[-1] in depth:
            # Delete the key-pair value from the sub-dict
            del depth[true_path[-1]]
        else:
            logger.warning(f"Failed to delete {path} from cache! " f"Invalid path. Missing key at {true_path[-1]}")


def cached(path: list[str] | str) -> Callable:
    """
    A parameterized decorator that caches a given function under the key
    'root_key' and sub-key 'attr_key'.

    For example:

    '''
    @cached(['fancy', 'func'])
    def some_func():
        pass
    '''

    or alternatively:

    '''
    @cached("fancy.func")
    def some_func():
        pass
    '''

    would cache some_func under:

    '''
    get_cache()['fancy']['func']
    '''

    Args:
       path: A list of strings or a string following dot-notation that describes
       the dict-path where the element should be stored.

    Returns: The base-level decorator

    Raises:
        KeyError: The path provided was invalid.
    """

    def decorate(func: Callable):
        cache_element(path, func)

        return func

    return decorate


def loader(cls: str | type):
    """
    A wrapper for the @cached decorator that pre-populates the path for JSON
    loader functions.

    This decorator also performs inspections on the JSON loader function to
    ensure it accepts the appropriate inputs.

    Args:
        cls: The type or name of type to store the loader in.

    Returns: The base decorator generated by the internal @cached decorator

    Raises:
        KeyError: The class provided has no Loader stored in the cache
    """
    from game.structures.loadable import LoadableMixin

    true_class: str = cls if isinstance(cls, str) else cls.__name__
    return cached([LoadableMixin.LOADER_KEY, true_class, LoadableMixin.ATTR_KEY])


"""
Methods for managing storage.

While the cache is a good location to leave things for general access,
storage is intended to be used privately between StateDevices. As such, its 
usage is strictly moderated by the accessors defined here.
"""


def request_storage_key() -> str:
    """
    Reserve a unique key in the storage system.
    """
    global storage

    current_key: uuid.UUID = uuid.uuid4()

    while current_key.__str__() in storage:
        current_key = uuid.uuid4()

    # Once a new key is secured, add it to the storage and set it to None.
    # Then, return the key
    storage[current_key.__str__()] = None
    return current_key.__str__()


def from_storage(key: str, delete: bool = False) -> any:
    """
    Retrieve a value from storage.

    If delete == True, delete the value from storage.
    """
    global storage

    val = storage[key]

    if delete:
        del storage[key]

    return val


def store_element(storage_key: str, value: any) -> None:
    """
    Store an element in the storage dict.

    Since the storage dict is shallow (1D), there's no need for complex decoding
    like in the cache
    """

    global storage

    if storage_key not in storage:
        raise KeyError(f"No such storage key: {storage_key}")

    storage[storage_key] = value
