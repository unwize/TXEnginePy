from __future__ import annotations

from enum import Enum


import game
import game.systems.item as items
from game.cache import cached, from_cache, from_storage
from game.structures.enums import InputType, TargetMode
from game.structures.loadable import LoadableMixin
from game.structures.messages import ComponentFactory, StringContent
from game.structures.state_device import FiniteStateDevice
from game.systems.combat.combat_engine.choice_data import ChoiceData
from game.systems.combat.combat_engine.inspect_entity_event import InspectEntityEvent
from game.systems.event import Event
from game.systems.event.select_element_event import SelectElementEventFactory
from game.systems.event.select_item_event import SelectItemEvent


class PlayerCombatChoiceEvent(Event):
    """
    Guides the player through choosing an action to take for a given entity during Combat
    """

    class States(Enum):
        DEFAULT = 0  # Setup
        CHOOSE_TURN_OPTION = 1  # Show the user which options are available
        CHOOSE_AN_ABILITY = 2  # Show the user abilities and request a selection
        CHOOSE_SINGLE_ABILITY_TARGET = 3  # If the ability requires a target, show available targets
        CONFIRM_GROUP_ABILITY_TARGET = 4  # If the ability targets a group, confirm
        CANNOT_USE_ABILITY = 5  # If the ability cannot be user for some reason, say so
        CHOOSE_AN_ITEM = 6  # Show the user all available items and request a selection
        DETECT_ITEM_USABLE = 7  # Check if the user can use the item and go to the appropriate state
        CANNOT_USE_ITEM = 8  # If the item cannot be used for some reason, say so
        SUBMIT_CHOICE = 9  # Once all choices have been finalized, submit them to the global combat instance
        PASS_TURN = 10  # If the choice was to pass, do so
        LIST_ENEMIES = 11  # Show a list of enemies that can be inspected
        LIST_ALLIES = 12  # SHow a list of allies that can be inspected
        INSPECT_ENTITY = 13  # SHow details about a specific entity
        CHECK_ABILITY_USABLE = 14  # Verify that selected ability can be used
        TERMINATE = -1  # Clean up

    def _get_turn_choices(self) -> dict[str, States]:
        return {
            "Inspect enemies": self.States.LIST_ENEMIES,
            "Inspect allies": self.States.LIST_ALLIES,
            "Use an ability": self.States.CHOOSE_AN_ABILITY,
            "Use an item": self.States.CHOOSE_AN_ITEM,
            "Pass turn": self.States.PASS_TURN,
        }

    def __init__(self, entity):
        super().__init__(InputType.SILENT, self.States, self.States.DEFAULT)
        self._links: dict[str, dict[str, str]] = {}
        self._entity = entity  # The entity for which to make a choice
        self._choice_data: ChoiceData = None
        self._available_turn_choices: dict[str, PlayerCombatChoiceEvent.States] = self._get_turn_choices()

        from game.systems.entity.entities import CombatEntity

        if not isinstance(self._entity, CombatEntity):
            raise TypeError(f"Invalid type for field `entity`! Expected CombatEntity, got {type(entity)}")

        self._setup_states()

    def _setup_states(self) -> None:
        @self.state_logic(self.States.DEFAULT, InputType.SILENT)
        def _logic(_: any) -> None:
            self.set_state(self.States.CHOOSE_TURN_OPTION)

        # SHOW_OPTIONS
        FiniteStateDevice.user_branching_state(
            self, self.States.CHOOSE_TURN_OPTION, self._available_turn_choices, "What would you like to do?"
        )

        # CHOOSE_AN_ABILITY
        @self.state_logic(self.States.CHOOSE_AN_ABILITY, InputType.SILENT)
        def _logic(_: any) -> None:
            choose_ability_event = SelectElementEventFactory.get_select_ability_event(self._entity, False, False)
            self._links["CHOOSE_AN_ABILITY"] = choose_ability_event.link()
            game.add_state_device(choose_ability_event)
            self.set_state(self.States.CHECK_ABILITY_USABLE)

        # CHECK_ABILITY_USABLE
        @self.state_logic(self.States.CHECK_ABILITY_USABLE, InputType.SILENT)
        def _logic(_: any) -> None:
            selected_ability = from_storage(self._links["CHOOSE_AN_ABILITY"]["selected_element"])

            # If selected_ability is None, then the player didn't select anything from the SelectAbilityEvent
            if selected_ability is None:
                self.set_state(self.States.CHOOSE_TURN_OPTION)

            # Check if the selected_ability is usable by the player
            elif not self._entity.ability_controller.is_ability_usable(selected_ability):
                self.set_state(self.States.CANNOT_USE_ABILITY)

            # Check if the ability targets a group. If so, go to the group target confirmation state
            elif from_cache("managers.AbilityManager").get_instance(selected_ability).target_mode in [
                TargetMode.ALL,
                TargetMode.ALL_ALLY,
                TargetMode.ALL_ENEMY,
            ]:
                self.set_state(self.States.CONFIRM_GROUP_ABILITY_TARGET)

            # The ability must be valid, and must be targeting a single target. Go to single target selection state
            else:
                self.set_state(self.States.CHOOSE_SINGLE_ABILITY_TARGET)

        # CHOOSE_ABILITY_TARGET
        @self.state_logic(
            self.States.CHOOSE_SINGLE_ABILITY_TARGET,
            InputType.INT,
            input_min=-1,
            input_max=lambda: len(
                from_cache("combat").get_valid_ability_targets(
                    self._entity, from_storage(self._links["CHOOSE_AN_ABILITY"]["selected_element"])
                )
            )
            - 1,
        )
        def _logic(entity_index: int) -> None:
            if entity_index == -1:
                self.set_state(self.States.CHOOSE_AN_ABILITY)
                return

            chosen_ability = from_storage(self._links["CHOOSE_AN_ABILITY"]["selected_element"])
            self._choice_data = ChoiceData(
                ChoiceData.ChoiceType.ABILITY,
                ability_name=chosen_ability,
                ability_target=from_cache("combat").get_valid_ability_targets(self._entity, chosen_ability)[
                    entity_index
                ],
            )
            self.set_state(self.States.SUBMIT_CHOICE)

        @self.state_content(self.States.CHOOSE_SINGLE_ABILITY_TARGET)
        def _content() -> dict:
            chosen_ability = from_storage(self._links["CHOOSE_AN_ABILITY"]["selected_element"])
            targets = from_cache("combat").get_valid_ability_targets(self._entity, chosen_ability)
            ci = from_cache("combat")

            return ComponentFactory.get(
                ["Select a target:"],
                [[f"{target.name} ({'ENEMY' if target in ci.enemies else 'ALLY'})" for target in targets]],
            )

        @self.state_logic(self.States.CONFIRM_GROUP_ABILITY_TARGET, InputType.AFFIRMATIVE)
        def _logic(user_input: bool) -> None:
            chosen_ability = from_storage(self._links["CHOOSE_AN_ABILITY"]["selected_element"])
            targets = from_cache("combat").get_valid_ability_targets(self._entity, chosen_ability)

            if user_input:
                self._choice_data = ChoiceData(
                    ChoiceData.ChoiceType.ABILITY, ability_name=chosen_ability, ability_target=targets
                )
                self.set_state(self.States.SUBMIT_CHOICE)
            else:
                self.set_state(self.States.CHOOSE_AN_ABILITY)

        @self.state_content(self.States.CONFIRM_GROUP_ABILITY_TARGET)
        def _content() -> dict:
            ci = from_cache("combat")
            chosen_ability = from_storage(self._links["CHOOSE_AN_ABILITY"]["selected_element"])
            targets = from_cache("combat").get_valid_ability_targets(self._entity, chosen_ability)

            return ComponentFactory.get(
                [f"{chosen_ability} targets the following entities. Are you sure?"],
                [[f"{target.name} ({'ENEMY' if target in ci.enemies else 'ALLY'}), " for target in targets]],
            )

        # CANNOT_USE_ABILITY
        @self.state_logic(self.States.CANNOT_USE_ABILITY, InputType.ANY)
        def _logic(_: any) -> None:
            self.set_state(self.States.CHOOSE_TURN_OPTION)

        @self.state_content(self.States.CANNOT_USE_ABILITY)
        def _content() -> dict:
            return ComponentFactory.get(["You cannot use that Ability."])

        # CHOOSE_AN_ITEM
        @self.state_logic(self.States.CHOOSE_AN_ITEM, InputType.SILENT)
        def _logic(_: any) -> None:
            from game.systems.item.item import Usable

            # Generate a SelectItemEvent that only displays Usable Items
            select_usable_event = SelectItemEvent(self._entity, lambda item: isinstance(item, Usable))

            # Generate a storage link and cache it in _links
            self._links["CHOOSE_AN_ITEM"] = select_usable_event.link()

            # Add s_u_e to event stack
            game.add_state_device(select_usable_event)

            # Transition state
            self.set_state(self.States.DETECT_ITEM_USABLE)

        # DETECT_ITEM_USABLE
        @self.state_logic(self.States.DETECT_ITEM_USABLE, InputType.SILENT)
        def _logic(_: any) -> None:
            from game.systems.item.item import Usable

            # Decode the linked storage ID to retrieve the ID of the item selected by the user
            chosen_item_id = from_storage(self._links["CHOOSE_AN_ITEM"]["selected_item_id"])

            if chosen_item_id is None:
                self.set_state(self.States.CHOOSE_TURN_OPTION)  # Return to main state
                return

            instance_of_chosen_item: Usable = items.item_manager.get_instance(chosen_item_id)  # Of type Usable
            entity_can_use_item: bool = instance_of_chosen_item.is_requirements_fulfilled(
                self._entity
            )  # Store to avoid re-computation

            #  If the user actually chose an Item, store that info in a choice_data and move on
            if entity_can_use_item:
                self._choice_data = ChoiceData(ChoiceData.ChoiceType.ITEM, item_id=chosen_item_id)
                self.set_state(self.States.SUBMIT_CHOICE)

            # Entity fails requirements checks
            elif not entity_can_use_item:
                self.set_state(self.States.CANNOT_USE_ITEM)

            else:
                raise RuntimeError("Something went wrong with PlayerCombatChoiceEvent")

        # CANNOT_USE_ITEM
        @self.state_logic(self.States.CANNOT_USE_ITEM, InputType.ANY)
        def _logic(_: any) -> None:
            self.set_state(self.States.CHOOSE_AN_ITEM)

        @self.state_content(self.States.CANNOT_USE_ITEM)
        def _content() -> dict:
            item_instance = from_cache("managers.ItemManager").get_instance(self._choice_data.item_id)

            return ComponentFactory.get(
                ["You cannot use ", StringContent(value=item_instance.name, formatting="item_name"), "!"],
                item_instance.get_requirements_as_options(),
            )

        # SUBMIT_CHOICE
        @self.state_logic(self.States.SUBMIT_CHOICE, InputType.SILENT)
        def _logic(_: any) -> None:
            from_cache("combat").submit_entity_choice(self._entity, self._choice_data)
            self.set_state(self.States.TERMINATE)

        # PASS_TURN
        @self.state_logic(self.States.PASS_TURN, InputType.ANY)
        def _logic(_: any) -> None:
            self._choice_data = ChoiceData(ChoiceData.ChoiceType.PASS)
            self.set_state(self.States.SUBMIT_CHOICE)

        @self.state_content(self.States.PASS_TURN)
        def _content() -> dict:
            return ComponentFactory.get(
                [StringContent(value=self._entity.name, formatting="entity_name"), " chose not to act."]
            )

        # INSPECT_ALLIES
        @self.state_logic(self.States.LIST_ALLIES, InputType.SILENT)
        def _logic(_: any) -> None:
            event = SelectElementEventFactory.get_select_entity_event(from_cache("combat").allies)
            self._links["INSPECT_ENTITY"] = event.link()

            game.add_state_device(event)
            self.set_state(self.States.INSPECT_ENTITY)

        # INSPECT_ENEMIES
        @self.state_logic(self.States.LIST_ENEMIES, InputType.SILENT)
        def _logic(_: any) -> None:
            event = SelectElementEventFactory.get_select_entity_event(from_cache("combat").enemies)
            self._links["INSPECT_ENTITY"] = event.link()
            game.add_state_device(event)
            self.set_state(self.States.INSPECT_ENTITY)

        # INSPECT_ENTITY
        @self.state_logic(self.States.INSPECT_ENTITY, InputType.SILENT)
        def _logic(_: any) -> None:
            entity = from_storage(self._links["INSPECT_ENTITY"]["selected_element"], delete=True)

            # Make sure that an entity was selected in the previous state
            if entity is None:
                self.set_state(self.States.DEFAULT)  # If no entity was selected, go back to the default state
                return

            # Build an inspection event and add it to the stack
            event = InspectEntityEvent(target=entity)
            game.add_state_device(event)

            # Look back in the state history to the previous state (before this one). Use this to determine if the
            # Inspected entity was an ally or enemy. Accordingly, set the NEXT state back to the correct listing state
            if self.state_history[-2] in [self.States.LIST_ENEMIES, self.States.LIST_ALLIES]:
                self.set_state(self.state_history[-2])
            else:
                raise RuntimeError(f"Unexpected state history! state_history[-2] is {self.state_history[-2]}!")

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "PlayerCombatChoiceEvent", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> any:
        raise RuntimeError("Loading of PlayerCombatChoiceEvent from JSON is not supported!")
