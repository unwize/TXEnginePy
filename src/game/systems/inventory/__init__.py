from game.systems.inventory.equipment_controller import EquipmentController
from game.systems.inventory.equipment_manager import EquipmentManager
from game.systems.inventory.inventory_controller import InventoryController, Stack

equipment_manager = EquipmentManager()

__all__ = ["EquipmentController", "EquipmentManager", "InventoryController", "Stack"]
