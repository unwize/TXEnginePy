import asyncio
import json
import os
from abc import ABC

import requests
from loguru import logger
from rich import print

from websockets.asyncio.client import connect


class BaseViewer(ABC):
    """
    An abstract viewer class that implements common methods used for displaying content as simple text.
    """

    @classmethod
    def clear(cls) -> None:
        """
        Clear a terminal's contents

        Returns: None
        """
        os.system("cls")

    @classmethod
    def get_text_header(cls, tx_engine_response: dict) -> str:
        """
        For a given response from TXEngine, pull data regarding the user's response conditions, format it, and return it.

        Args:
            tx_engine_response: A JSON-derived dict containing a response from a TXEnginePy instance.

        Returns: Text to be used in the header of the display to the user

        """
        input_type = (
            tx_engine_response["input_type"]
            if type(tx_engine_response["input_type"]) is str
            else tx_engine_response["input_type"][0]
        )
        input_range = tx_engine_response["input_range"]

        formatting = ["italic"]

        match input_type:
            case "int":
                hdr = f"Enter a number between ({input_range['min']} and {input_range['max']}):"
            case "none":
                hdr = "Press any key:"
            case "str":
                hdr = "Enter a string: "

            case "affirmative":
                hdr = "Enter y, n, yes, or no:"
            case "any":
                hdr = "Press any key..."
            case _:
                logger.error(f"Unexpected input type: {input_type}")
                logger.debug(f"Failed frame: {str(tx_engine_response)}")
                raise ValueError(f"Unexpected input type: {input_type}")

        return cls.format_string(hdr, formatting)

    @classmethod
    def formatting_to_tags(cls, tags: list[str], opening_tag: bool = None, closing_tag: bool = None) -> str:
        buf = ""
        if opening_tag:
            for tag in tags:
                buf = buf + f"[{tag}]"

        elif closing_tag:
            for tag in tags:
                buf = buf + f"[/{tag}]"

        return buf

    @classmethod
    def format_string(cls, content: str, tags: list[str]) -> str:
        return cls.formatting_to_tags(tags, opening_tag=True) + content + cls.formatting_to_tags(tags, closing_tag=True)

    @classmethod
    def parse_content(cls, content: list) -> str:
        buf = ""
        for element in content:
            if type(element) is str:
                buf = buf + element
            elif type(element) is dict:
                buf = (
                    buf
                    + cls.formatting_to_tags(element["formatting"], opening_tag=True)
                    + element["value"]
                    + cls.formatting_to_tags(element["formatting"], closing_tag=True)
                )
        return buf

    def display(self, tx_engine_response: dict):
        """
        Primitively print GET results
        """
        self.clear()

        def entity_to_str(entity_dict: dict[str, any]) -> str:
            entity_name = entity_dict["name"]
            primary_resource_name = entity_dict["primary_resource_name"]
            primary_resource_value = entity_dict["primary_resource_val"]
            primary_resource_max = entity_dict["primary_resource_max"]
            return f"{entity_name}\n{primary_resource_name}]: [{primary_resource_value}/{primary_resource_max}]"

        if "enemies" in tx_engine_response["components"]:
            print("ENEMIES")
            for enemy in tx_engine_response["components"]["enemies"]:
                print(entity_to_str(enemy))

        if "allies" in tx_engine_response["components"]:
            print("ALLIES")
            for ally in tx_engine_response["components"]["allies"]:
                print(entity_to_str(ally))

        print(self.parse_content(tx_engine_response["components"]["content"]))

        if "options" in tx_engine_response["components"] and type(tx_engine_response["components"]["options"]) is list:
            for idx, opt in enumerate(tx_engine_response["components"]["options"]):
                print(f"[{idx}] {self.parse_content(opt)}")

        print(self.get_text_header(tx_engine_response))


class Viewer(BaseViewer):
    """
    A basic class that visualizes the TXEngine API
    """

    def __init__(self):
        u = input("Enter the IP for the TXEngine server: ")
        self._ip = "http://" + (u if u != "" else "localhost:8000")
        self._session = requests.Session()
        self.clear = lambda: os.system("cls")

    def start_session(self):
        """
        Start the core loop for getting/put API calls.
        """

        while True:
            results = self._session.get(self._ip, verify=False)
            self.display(results.json())
            user_input = input()

            self._session.put(self._ip, params={"user_input": user_input}, verify=False)


class WebsocketViewer(BaseViewer):
    """
    A primitive TXEngine client built for websocket connections.
    """

    def __init__(self):
        self._ip = input("Enter ip address (default: localhost)")
        if self._ip.strip() == "":
            self._ip = "localhost"

    async def client(self) -> None:
        async with connect(f"ws://{self._ip}:8000") as websocket:
            await websocket.send("{}")  # Ping to get a baseline response
            response = await websocket.recv()
            while True:
                self.clear()
                self.display(json.loads(response))
                payload = '{"user_input": ' + f'"{input()}"' + "}"  # Must follow the valid JSON structure requirements
                await websocket.send(payload)
                response = await websocket.recv()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "--ws":
            client = WebsocketViewer()
            asyncio.run(client.client())

    client = Viewer()
    client.start_session()
