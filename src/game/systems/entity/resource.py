import copy
import inspect

from loguru import logger

from game.cache import cached, from_cache, get_config
from game.structures.loadable import LoadableMixin
from game.structures.loadable_factory import LoadableFactory
from game.structures.messages import StringContent


class Resource:
    """
    Represents an entity resource, ex: Health, Mana, Stamina, etc
    """

    def __init__(self, name: str, max: int, description: str, value: int = None):
        if value is not None and value < 0:
            raise ValueError(f"Resource value is less than min! {value} < 0.")

        if value is not None and value > max:
            raise ValueError(f"Resource cannot have value above max! {value} > {max}")

        if name is None or name == "":
            raise ValueError("Resource must have a name!")

        if description is None or description == "":
            raise ValueError("Resource must have a description!")

        self.name = name
        self.base_max = self.max = max  # Base max being the base value, max being the current max due to modifiers
        self.description = description
        self.value = value or self.max

    @property
    def percent_remaining(self) -> float:
        """
        Calculates what percentage of the resource is remaining.
        """
        return float(self.value) / float(self.max)

    def test_adjust(self, amount: int | float) -> int:
        """
        Fake adjusts the value of the Resource. If amount is int, value is added to amount. If amount is float, value
        is added to (max*amount).

        Args:
            amount: An int or float that determines how the resource's value is changed.

        Returns:
            What the Resource's value would be after the adjustment
        """

        if type(amount) is int:
            return max(0, min(self.max, self.value + amount))

        elif type(amount) is float:
            return round(max(0, min(self.max, self.value + (self.max * amount))))

        else:
            raise TypeError(f"Cannot adjust Resource by type {type(amount)}! Must be int or float.")

    def adjust(self, amount: int | float) -> int:
        """
        Adjusts the value of the Resource. If amount is an int, value is added to amount. If amount is a float, value
        is added to (max*amount).

        Args:
            amount: An int or float that determines how the resource's value is changed.

        Returns:
            The Resource's value after the adjustment
        """

        self.value = self.test_adjust(amount)
        return self.value

    def __str__(self) -> str:
        return f"[{self.name}: {self.value}/{self.max}]"

    def __txengine__repr__(self) -> list[StringContent]:
        return [
            StringContent(value="["),
            StringContent(value=self.name, formatting="resource_name"),
            StringContent(value=": "),
            StringContent(value=str(self.value), formatting="resource_value"),
            StringContent(value="/"),
            StringContent(value=str(self.max), formatting="resource_max"),
            StringContent(value="]"),
        ]

    def __repr__(self):
        return self.__str__()

    @staticmethod
    @cached([LoadableMixin.LOADER_KEY, "Resource", LoadableMixin.ATTR_KEY])
    def from_json(json: dict[str, any]) -> "Resource":
        """
        Create a Resource object from a JSON blob

        Required JSON fields:
        - name: str
        - value: int
        - max: int
        - description: str

        Optional JSON fields:
        - None
        """

        required_fields: list = [("name", str), ("description", str), ("max", int)]

        optional_fields: list = [("value", int)]

        LoadableFactory.validate_fields(required_fields, json)
        LoadableFactory.validate_fields(optional_fields, json, False, False)

        if json["class"] != "Resource":
            raise TypeError()

        return Resource(
            json["name"],
            json["max"],
            json["description"],
            **LoadableFactory.collect_optional_fields(optional_fields, json),
        )


class ResourceModifierMixin:
    """
    This mixin allows an object to be attached as a modifier to one or more Resources via the ResourceController

    A modifier dict is structured where resource_name (str) : modifier (int)

    For example:
        {
            "health" : 10,
            "stamina" : -5,
            "mana" : 0.25,
            "faith" : 0.1
        }

    Would set up a modifier for +10 health, -5 stamina, +25% mana, -10% faith.
    """

    @classmethod
    def validate_modifier(cls, resource_name, modifier):
        if type(resource_name) is not str:
            raise TypeError(f"Invalid resource name: {resource_name}! Must be a str!")

        if type(modifier) is not int and type(modifier) is not float:
            raise TypeError(f"Invalid resource modifier: {modifier}! Must be an int or float.")

        if modifier == 0:
            raise ValueError(f"Modifier of {resource_name} cannot be 0!")

    def __init__(self, resource_modifiers: dict[str, int | float] = None, **kwargs):
        super().__init__(**kwargs)

        # Validate modifier dict structure and values
        if resource_modifiers is not None:
            for res_name, mod in resource_modifiers.items():
                self.validate_modifier(res_name, mod)

        self.resource_modifiers: dict[str, int | float] = resource_modifiers or {}


class ResourceController:
    """
    A controller that manages an individual entity's resources.
    """

    def __init__(self, resources: list[tuple[str, int, int] | Resource] = None):
        self.resources: dict[str, dict[str, any]] = {
            r.name: {
                "instance": r,
                "modifiers": {
                    "int": [],
                    "float": [],
                },
            }
            for r in from_cache("managers.ResourceManager").all_resources
        }

        if resources:
            if type(resources) is not list:
                raise TypeError(f"ResourceController.resources must be of type list! Got {type(resources)} instead.")

            for overloaded_resource in resources:
                if type(overloaded_resource) is Resource:
                    if overloaded_resource.name not in self.resources:
                        raise ValueError(
                            f"Cannot overload a resource that doesn't exist! Unknown resource: {overloaded_resource.name}"
                        )

                    self.set_instance(copy.deepcopy(overloaded_resource))

                elif type(overloaded_resource) is tuple[str, int, int]:
                    if overloaded_resource[0] not in self.resources:
                        raise ValueError(
                            f"Cannot overload a resource that doesn't exist! Unknown resource: {overloaded_resource[0]}"
                        )

                    self.get_instance(overloaded_resource[0]).value = overloaded_resource[1]
                    self.get_instance(overloaded_resource[0]).max = overloaded_resource[2]

    def __contains__(self, resource: str | Resource) -> bool:
        if type(resource) is str:
            return resource in self.resources
        elif type(resource) is Resource:
            return resource.name in self.resources

        return False

    def __getitem__(self, item):
        if type(item) is str:
            return self.get_instance(item)
        else:
            raise KeyError("resource_name must be str!")

    @property
    def primary_resource(self) -> "Resource":
        return self[get_config()["resources"]["primary_resource"]]

    def get_instance(self, resource_name) -> Resource:
        """
        Get a live-instance of the Resource object within the ResourceController
        """
        try:
            return self.resources[resource_name]["instance"]
        except KeyError as e:
            logger.error(f"No resource {resource_name} found!")
            logger.debug(f"Available resources: {self.resources.items()}")
            raise e

    def set_instance(self, resource: Resource) -> None:
        """
        Set the live-instance of the Resource object within the ResourceController to a new Resource object
        """
        if resource.name not in self.resources:
            raise ValueError(f"Unknown resource {resource.name}!")

        self.resources[resource.name]["instance"] = resource

    def get_modifiers(self, resource_name, modifier_type: str | type) -> list[ResourceModifierMixin]:
        """
        Retrieve the modifiers for a given resource and modifier type
        """

        if resource_name not in self.resources:
            raise ValueError(f"Unknown resource: {resource_name}!")

        if type(modifier_type) is str:
            true_modifier_type = modifier_type
        elif inspect.isclass(modifier_type):
            true_modifier_type = modifier_type.__name__
        else:
            raise TypeError(f"Unknown modifier type: {type(modifier_type)}")

        if true_modifier_type not in ["int", "float"]:
            raise ValueError(f"Unknown modifier type: {modifier_type}!")

        return self.resources[resource_name]["modifiers"][true_modifier_type]

    def attach_modifier(self, modifier: ResourceModifierMixin) -> None:
        """
        For each resource specified in the modifier object, attach a reference to it inside the controller and remove
        any cached maxes.
        """

        if not isinstance(modifier, ResourceModifierMixin):
            raise TypeError(f"Unexpected modifier type {type(modifier)}!")

        for resource_name in modifier.resource_modifiers:
            if resource_name not in self.resources:
                raise ValueError(f"Unknown resource: {resource_name}!")

            # Determine if the modifier is float or int typed and assign it accordingly
            if type(modifier.resource_modifiers[resource_name]) is int:
                self.get_modifiers(resource_name, int).append(modifier)

            elif type(modifier.resource_modifiers[resource_name]) is float:
                self.get_modifiers(resource_name, float).append(modifier)
            else:
                raise ValueError(f"Unknown modifier type: {type(modifier.resource_modifiers[resource_name])}!")

            self.get_instance(resource_name).max = self.compute_max(resource_name)

    def detach_modifier(self, modifier: ResourceModifierMixin) -> None:
        """
        Search through the list of attached modifiers and remove any references to the specified object
        """

        for resource_name in modifier.resource_modifiers:
            if resource_name not in self.resources:
                raise ValueError(f"Unknown resource: {resource_name}!")

            # Determine if the modifier is float or int typed and assign it accordingly
            if type(modifier.resource_modifiers[resource_name]) is int:
                if modifier in self.get_modifiers(resource_name, int):
                    self.get_modifiers(resource_name, int).remove(modifier)
                else:
                    raise RuntimeError(f"Unable to detach modifier {str(modifier)}! No such object attached.")

            elif type(modifier.resource_modifiers[resource_name]) is float:
                if modifier in self.get_modifiers(resource_name, float):
                    self.get_modifiers(resource_name, float).remove(modifier)
                else:
                    raise RuntimeError(f"Unable to detach modifier {str(modifier)}! No such object attached.")

            else:
                raise TypeError()

            # Recompute the max for the Resource
            self.resources[resource_name]["instance"].max = self.compute_max(resource_name)

    def compute_max(self, resource_name: str) -> int:
        """
        Compute the maximum value of the specified resource via modifier
        """

        if resource_name not in self.resources:
            raise ValueError(f"Unknown resource {resource_name}!")

        computed_max: int = self.get_base_max(resource_name)  # Base value from Resource.max

        # Compute the total % change specified by the float-based modifiers
        percent_change: float = 0.0
        for modifier in self.get_modifiers(resource_name, float):
            if not isinstance(modifier, ResourceModifierMixin):
                raise TypeError(f"Unexpected ResourceModifier type: {type(modifier)}")

            percent_change += modifier.resource_modifiers[resource_name]

        computed_max += computed_max * percent_change

        # Compute the total flat changed specified by the int-based modifiers
        flat_change: int = 0
        for modifier in self.get_modifiers(resource_name, int):
            if not isinstance(modifier, ResourceModifierMixin):
                raise TypeError(f"Unexpected ResourceModifier type: {type(modifier)}")

            flat_change += modifier.resource_modifiers[resource_name]

        computed_max += flat_change

        return round(computed_max)

    def get_value(self, resource_name: str) -> int:
        """
        Get the current value of a given resource
        """
        return self.get_instance(resource_name).value

    def get_max(self, resource_name: str) -> int:
        """
        Get the current max-value of a given resource
        """
        return self.get_instance(resource_name).max

    def get_base_max(self, resource_name: str) -> int:
        """
        Get the base maximum value of the given resource
        """
        return self.get_instance(resource_name).base_max

    def get_resource_as_option(self, resource_name: str) -> list[str | StringContent]:
        return [str(self.get_instance(resource_name))]

    def get_resources_as_options(self) -> list[list[str | StringContent]]:
        return [self.get_resource_as_option(res) for res in self.resources]
