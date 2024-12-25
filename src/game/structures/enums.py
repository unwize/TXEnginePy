import enum


class InputType(enum.Enum):
    AFFIRMATIVE = "affirmative"  # Get a yes or no
    INT = "int"  # Get an int
    STR = "str"  # Get a string
    SILENT = "silent"  # Operate silently, don't attempt to prompt user
    ANY = "any"  # Get any key value as a response. Useful to simply prompt the user to continue


class CombatPhase(enum.Enum):
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

    START_PHASE = "start_phase"
    PRE_ACTION_PHASE = "pre_action_phase"
    ACTION_PHASE = "action_phase"
    POST_ACTION_PHASE = "post_action_phase"
    END_PHASE = "end_phase"


class TargetMode(enum.Enum):
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

    ALL = "all"  # Targets every entity simultaneously
    SINGLE = "single"  # Targets any single entity
    SINGLE_ALLY = "single_ally"  # Targets a single ally
    SINGLE_ENEMY = "single_enemy"  # Targets a single enemy
    ALL_ALLY = "all_allies"  # Targets all allies simultaneously
    ALL_ENEMY = "all_enemies"  # Targets all enemies simultaneously
    NOT_SELF = "not_self"  # Targets any entity that isn't the caster
    SELF = "self"  # Targets the caster


class EquipmentType(enum.Enum):
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

    WEAPON = "weapon"
    # Armor
    HEAD = "head"
    CHEST = "chest"
    HANDS = "hands"
    LEGS = "legs"
    FEET = "feet"
    # Jewelry
    RING = "ring"
    NECKLACE = "necklace"
