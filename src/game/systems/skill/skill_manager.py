from __future__ import annotations

import copy

from game.structures.loadable_factory import LoadableFactory
from game.structures.manager import Manager
import game.systems.skill.skills as skills
from game.util.asset_utils import get_asset


class SkillManager(Manager):
    SKILL_ASSET_PATH = "skills"

    def __init__(self):
        super().__init__()
        self._manifest: dict[int, skills.Skill] = {}

    def __getitem__(self, item) -> skills.Skill:
        return self.get_skill(item)

    def __contains__(self, item) -> bool:
        return self._manifest.__contains__(item)

    def __iter__(self):
        return self._manifest.__iter__()

    def register_skill(self, skill: skills.Skill) -> None:
        if not isinstance(skill, skills.Skill):
            raise TypeError(f"Expected object of type skills.Skill, got {type(skill)} instead!")

        if skill.id in self._manifest:
            raise ValueError(f"skills.Skill with id {skill.id} already registered!")

        self._manifest[skill.id] = skill

    def get_skill(self, skill_id: int) -> skills.Skill:
        if type(skill_id) is not int:
            raise TypeError(f"Expected skill_id of type int, got {type(skill_id)} instead!")
        if skill_id not in self._manifest:
            raise ValueError(f"No skill with id {skill_id}!")

        return copy.deepcopy(self._manifest[skill_id])

    def load(self) -> None:
        raw_asset: dict[str, any] = get_asset(self.SKILL_ASSET_PATH)

        for raw_skill in raw_asset["content"]:
            skill = LoadableFactory.get(raw_skill)

            if not isinstance(skill, skills.Skill):
                raise TypeError(f"Expected object of type Skill, got {type(skill)} instead!")

            self.register_skill(skill)

    def save(self) -> None:
        pass
