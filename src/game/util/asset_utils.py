"""
Asset utils defines useful functions for accessing and transforming text-based assets stored on disk.

The primary use for assets is storing json-based information. For example, items.json would store json-form
representations of Item objects.

For more information about how different classes are loaded from JSON, visit their respective Manager classes or view
their respective class-defined 'from_json' methods.
"""

import json
import os
from os.path import exists
from typing import IO

from loguru import logger

DEFAULT_ASSET_PATH = "./assets"
DEFAULT_ASSET_TYPE = "json"

asset_handlers = {}


def asset_handler(file_type: str):
    global asset_handlers
    if file_type in asset_handlers:
        raise ValueError(f"Handler for asset file type {file_type} already registered!")

    if not file_type.isalnum():
        raise ValueError(f"{file_type} is not a valid file type! Files types may only contain letters and numbers!")

    def decorate(fn):
        if not callable(fn):
            raise TypeError(f"Cannot register type {type(fn)} as handler! Expected callable!")

        asset_handlers[file_type] = fn

        return fn

    return decorate


def get_asset(asset_name: str, file_type: str = DEFAULT_ASSET_TYPE) -> any:
    """
    Access a text asset stored on the local disk.

    get_asset locates a handler assigned to the provided 'file_type' and calls it to handle the parsing of the asset.

    args:
        asset_name: The file name of the asset, excluding file extension.
        file_type: The file extension of the asset. Default is 'json'.

    Returns: A parsed representation of the asset. This may take the form of a dict, list, or other collection.
    """
    if file_type not in asset_handlers:
        raise ValueError(f"No handler registered for file type {file_type}!")

    full_path = f"{DEFAULT_ASSET_PATH}/{asset_name}.{file_type}"

    if not exists(full_path):
        raise FileNotFoundError(
            f"Cannot locate asset {asset_name}.{file_type}!\nWorking dir: {os.getcwd()}\nAsset "
            f"path: {DEFAULT_ASSET_PATH}"
        )

    return asset_handlers[file_type](open(full_path, "r"))


@asset_handler("json")
def json_handler(raw_file_text: IO) -> dict:
    try:
        payload = json.loads(raw_file_text.read())
    except json.decoder.JSONDecodeError as e:
        logger.error("JSON formatting error in file!")
        raw_file_text.close()
        raise e

    raw_file_text.close()
    return payload
