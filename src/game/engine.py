"""
Houses the primary logical driver logic for starting TXEngine. Responsible for
initiating IO, reading and executing config, and more.
"""

import os.path

from loguru import logger
from omegaconf import OmegaConf

# These imports rescue stranded from_json declarations. Removing them prevents
# the interpreter from finding and caching those functions. Do not remove.
from game.systems.room.action.manage_equipment_action import *
from game.systems.room.action.manage_inventory_action import *
from game.systems.room.action.dialog_action import *
from game.systems.requirement.item_requirement import *
from game.systems.dialog import *
from game.systems.room.action.shop_action import *
from game.systems.event.view_summary_event import *
from game.systems.event.dialog_event import *
from game.systems.inventory.structures import *


from .cache import get_config, set_config, get_cache, from_cache
from .formatting import register_arguments, register_style
from .systems.entity.entities import Player

conf_dir_path: str = "./config/"
conf_file_path: str = "conf.yaml"
style_file_path: str = "styles.yaml"
conf_path: str = conf_dir_path + conf_file_path
style_path: str = conf_dir_path + style_file_path


class Engine:
    """
    A high-level manager that coordinates disk-io, config manipulation, loading
    content, saving content, and more.
    """

    # An explicit order for order-dependant managers. Any managers not listed
    # will be loaded in random order after the lowest priority (the largest int)
    manager_load_priority = {
        0: ["CurrencyManager", "ResourceManager", "FlagManager"],
        1: ["EquipmentManager"],
        2: ["ItemManager", "LootManager"],
        3: ["EntityManager"],
        4: ["RoomManager"],
    }

    @classmethod
    def get_manager_priority(cls, manager_cls: str | type) -> int | None:
        """
        Retrieve the priority of a manager class

        args:
            manager_cls : The name of the class of the manager, or the class of
            the manager

        returns:
            The priority of the manager class if it has been set, otherwise None
        """

        if isinstance(manager_cls, str):
            true_cls = manager_cls
        elif isinstance(manager_cls, type):
            true_cls = manager_cls.__name__
        else:
            raise TypeError(f"Expect str or type for manager_cls. Got type {type(manager_cls)} instead!")

        for priority in cls.manager_load_priority:
            if true_cls in cls.manager_load_priority[priority]:
                return priority

        return None

    @classmethod
    def set_manager_priority(cls, manager_cls: str | type, priority: int) -> None:
        """
        Set a manager's loading priority.

        Priorities with lower numerical values are loaded sooner.

        Args:
            manager_cls: The name of the class of the manager
            priority: The priority of the loading.

        Returns: None
        """

        # Type checking
        if not isinstance(priority, int):
            raise TypeError(f"Cannot set priority to type {type(priority)}. Priority must be an int!")
        if priority < 0:
            raise ValueError(f"Invalid priority: {priority}. Priority must be positive or zero!")

        if isinstance(manager_cls, str):
            true_cls = manager_cls
        elif isinstance(manager_cls, type):
            true_cls = manager_cls.__name__
        else:
            raise TypeError(f"Expect str or type for manager_cls. Got type {type(manager_cls)} instead!")

        # Check if the manager has already been assigned a priority.
        # If so, remove it from the extant list
        extant_priority = cls.get_manager_priority(true_cls)
        if extant_priority is not None:
            cls.manager_load_priority[extant_priority].remove(true_cls)

        # Check if the that priority already has a mapped list. If not, make one
        if priority not in cls.manager_load_priority:
            cls.manager_load_priority[priority] = []

        # Assign priority in map
        cls.manager_load_priority[priority].append(true_cls)

    def _debug_init_early(self) -> None:
        """
        A special function that runs before startup to support debugging efforts.
        Returns: None
        """

    def _debug_init_late(self) -> None:
        """
        A special function that runs post-startup to support debugging efforts.
        Returns:
        """

        get_cache()["player"] = Player(id=0, name="Player")
        p: Player = get_cache()["player"]
        p.coin_purse.adjust(0, 100)
        p.inventory.new_stack(1, 1)
        p.inventory.new_stack(3, 15)
        p.crafting_controller.learn_recipe(1)
        p.ability_controller.learn("Proto Ability")
        p.ability_controller.learn("My Opinions on Facebook are Really Important")
        p.ability_controller.learn("Shortcuts are Great")

    def _load_assets(self) -> None:
        """
        A startup phase method that loads JSON assets from disk
        """

        # Get a list of all managers
        manager_keys: list[str] = list(from_cache("managers").keys())

        # Get an ordered list of available priorities in ascending order
        ordered_priorities = list(self.manager_load_priority)
        ordered_priorities.sort()

        # Starting lowest, for each priority load the managers at that level
        for priority_level in ordered_priorities:
            for manager_key in self.manager_load_priority[priority_level]:
                logger.debug(f"[{manager_key}] Loading assets")

                # Fetch manager from cache and load
                from_cache(["managers", manager_key]).load()

                # Remove it from the list of remaining managers
                manager_keys.remove(manager_key)

        # For each manager that has no priority, load it
        for leftover_key in manager_keys:
            logger.debug(f"[{leftover_key}] Loading assets")

            # Fetch from cache and load manager
            from_cache(["managers", leftover_key]).load()

    def _startup(self):
        """
        Perform required startup logic

        Returns: None
        """
        self._debug_init_early()
        logger.info("Loading config...")
        # Load config values from disk
        if os.path.exists(conf_path):
            # Load config data
            set_config(OmegaConf.load(conf_path))

        else:
            set_config(OmegaConf.create(self.get_default_conf()))
            self.write_conf()

        logger.info("Loading styles...")
        if os.path.exists(style_path):
            # Load style data
            raw_style = OmegaConf.load(conf_dir_path + style_file_path)
            register_arguments(raw_style.arguments)
            for style in raw_style.get("styles").items():
                register_style(*style)
        else:
            self.write_styles()
            raise IOError("No styles.yaml! Generating empty styles...")

        get_cache()["player_location"] = get_config()["room"]["default_id"]

        self._load_assets()
        self._debug_init_late()

    def _shutdown(self):
        """
        Perform required shutdown logic

        Returns: None
        """

        # Save state data to disk
        for manager in get_cache()["managers"]:
            get_cache()["managers"][manager].save()

    def __init__(self):
        self._startup()  # Call startup logic.

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._shutdown()

    @staticmethod
    def get_default_conf() -> dict[str, any]:
        """

        Returns:

        """
        return {
            "io": {"save_data_path": "./saves", "asset_path": "./assets"},
            "inventory": {"default_capacity": 10},
            "room": {"default_id": 0},
        }

    @classmethod
    def write_styles(cls) -> None:
        """
        Write an empty styles file to disk.

        Returns: None
        """
        logger.info("Writing empty style file...")
        styles_empty = {"arguments": [], "styles": {}}

        if not os.path.exists(conf_dir_path):
            try:
                os.mkdir(conf_dir_path)
            except FileExistsError:
                logger.info("Config folder exists, skipping....")

            f = open(style_path, "x")
            f.close()
        OmegaConf.save(styles_empty, style_path)

    @classmethod
    def write_conf(cls) -> None:
        """
        Write a default config file to disk

        Returns: None

        """
        logger.info("Writing default config...")
        if not get_config():
            raise ValueError("Engine::conf must not be None!")

        if not os.path.exists(conf_dir_path):
            try:
                os.mkdir(conf_dir_path)
            except FileExistsError:
                logger.info("Config folder exists, skipping....")

            with open(conf_path, "x") as f:
                f.close()
            OmegaConf.save(get_config(), conf_path)
