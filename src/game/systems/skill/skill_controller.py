from game.structures.messages import StringContent
from game.systems.skill import skill_manager
from game.systems.skill.skills import Skill


class SkillController:
    """
    Manages the Skill instances for a specific Entity.
    """

    def __init__(self, obtain_all: bool = False, skill_ids: list[int] = None):
        """
        Args:
            obtain_all (bool): If True, get all skills from the skill_manager
            skill_ids (list[int]): If obtain_all is False and skill_ids is not None, obtain all the Skills in this list
        """

        if type(obtain_all) is not bool:
            raise TypeError()

        if type(skill_ids) is not None and type(skill_ids) is not list and not obtain_all:
            raise TypeError()

        self.obtain_all = obtain_all  # Marks if all the skills that exist have already been obtained
        self.skills: dict[int, Skill] = {}

        if obtain_all:
            for skill_id in skill_manager:
                self.obtain_skill(skill_id)

        elif skill_ids is not None:
            for skill_id in skill_ids:
                self.obtain_skill(skill_id)

    def __contains__(self, item: int) -> bool:
        return self.skills.__contains__(item)

    def __getitem__(self, item: int) -> Skill:
        return self.skills.__getitem__(item)

    def obtain_skill(self, skill_id: int) -> None:
        """
        Obtain a skill that has not already been added to the controller from the manager
        """

        if skill_id in self.skills:
            raise RuntimeError(f"Skill with id {skill_id} has already been obtained!")

        self.skills[skill_id] = skill_manager.get_skill(skill_id)

    def get_level(self, skill_id: int) -> int:
        """
        Fetch a skill's level by looking up its ID.
        """

        if skill_id not in self.skills:
            raise ValueError(f"No skill with id {skill_id} found!")

        return self.skills[skill_id].level

    def get_skill_as_option(self, skill_id: int) -> list[str | StringContent]:
        return [
            StringContent(value=self.skills[skill_id].name, formatting="skill_name"),
            f" lvl:{self.skills[skill_id].level}  [{self.skills[skill_id].xp}",
            f"/{self.skills[skill_id].level_up_limit}] ",
            f"({round((self.skills[skill_id].xp / self.skills[skill_id].level_up_limit) * 100)}%)",
        ]

    def get_skills_as_options(self) -> list[list[str | StringContent]]:
        return [self.get_skill_as_option(s) for s in self.skills]
