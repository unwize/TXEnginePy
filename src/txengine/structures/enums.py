import enum


class EquipmentType(enum.Enum):
    WEAPON = 0,
    # Armor
    HEAD = 1,
    CHEST = 2,
    HANDS = 3,
    LEGS = 4,
    FEET = 5,
    # Jewelry
    RING = 6,
    NECKLACE = 7


class InputType(enum.Enum):
    AFFIRMATIVE = 0,
    INT = 1,
    STR = 2
