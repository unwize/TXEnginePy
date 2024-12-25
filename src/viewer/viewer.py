import os

import requests
from loguru import logger
from rich import print


def formatting_to_tags(tags: list[str], opening_tag: bool = None, closing_tag: bool = None) -> str:
    buf = ""
    if opening_tag:
        for tag in tags:
            buf = buf + f"[{tag}]"

    elif closing_tag:
        for tag in tags:
            buf = buf + f"[/{tag}]"

    return buf


def format_string(content: str, tags: list[str]) -> str:
    return formatting_to_tags(tags, opening_tag=True) + content + formatting_to_tags(tags, closing_tag=True)


def parse_content(content: list) -> str:
    buf = ""
    for element in content:
        if type(element) is str:
            buf = buf + element
        elif type(element) is dict:
            buf = (
                buf
                + formatting_to_tags(element["formatting"], opening_tag=True)
                + element["value"]
                + formatting_to_tags(element["formatting"], closing_tag=True)
            )
    return buf


class Viewer:
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

    def get_text_header(self, tx_engine_response: dict) -> str:
        input_type = (
            tx_engine_response["input_type"]
            if type(tx_engine_response["input_type"]) is str
            else tx_engine_response["input_type"][0]
        )
        input_range = tx_engine_response["input_range"]

        formatting = ["italic"]

        if input_type == "int":
            hdr = f"Enter a number between ({input_range['min']} and {input_range['max']}):"

        elif input_type == "none":
            hdr = "Press any key:"

        elif input_type == "str":
            hdr = "Enter a string: "

        elif input_type == "affirmative":
            hdr = "Enter y, n, yes, or no:"
        elif input_type == "any":
            hdr = "Press any key..."
        else:
            logger.error(f"Unexpected input type: {input_type}")
            logger.debug(f"Failed frame: {str(tx_engine_response)}")
            raise ValueError(f"Unexpected input type: {input_type}")

        return format_string(hdr, formatting)

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

        print(parse_content(tx_engine_response["components"]["content"]))

        if "options" in tx_engine_response["components"] and type(tx_engine_response["components"]["options"]) is list:
            for idx, opt in enumerate(tx_engine_response["components"]["options"]):
                print(f"[{idx}] {parse_content(opt)}")

        print(self.get_text_header(tx_engine_response))


if __name__ == "__main__":
    viewer = Viewer()
    viewer.start_session()
