from __future__ import annotations

from game.systems.skill.skill_controller import SkillController


class SkillMixin:
    """
    A mixin that gives an entity access to a SkillController
    """

    def __init__(self, skills: dict[str, dict[str, int]] = None, **kwargs):
        super().__init__(**kwargs)
        """
        Expects a dict-form manifest formatted like so:
        {
            "skill_id" : {
                "level" : 1
                "xp" : 1
            }
        }
        """

        self.skill_controller = SkillController(obtain_all=True)

        if skills is not None and type(skills) is not dict:
            raise TypeError(f"Unexpected type for skills! Expected either dict or None, got {type(skills)} instead.")

        # Iterate through the skill dicts provided, and load them into the controller's data
        if skills is not None:
            for skill_id in skills:
                # JSON does not allow for int-typed keys, so we have to cast the str-equivalent of int back into an int
                try:
                    true_id = int(skill_id)
                except ValueError:
                    raise ValueError(f"ID of {skill_id} cannot be converted to int!")

                if true_id not in self.skill_controller and self.skill_controller.obtain_all:
                    raise ValueError(f"No skill with id {true_id}!")
                elif true_id not in self.skill_controller and not self.skill_controller.obtain_all:
                    self.skill_controller.obtain_skill(true_id)

                for term in ["level", "xp"]:
                    if term not in skills[skill_id]:
                        raise ValueError(f"Missing field {term} in skill definition for skill {skill_id}")

                # Finally, set the level and xp values of the skill (assuming it has already been obtained)
                self.skill_controller[true_id].level = skills[skill_id]["level"]
                self.skill_controller[true_id].xp = skills[skill_id]["xp"]
