from game.cache import from_cache
from game.systems.entity.entities import CombatEntity
from game.systems.requirement.requirements import SkillRequirement
from game.systems.skill.skills import Skill


def test_trivial():
    # Attempt to fetch a skill with id 1 from manager
    skill_instance: Skill = from_cache("managers.SkillManager").get_skill(1)

    # Check its actually a skill
    assert isinstance(skill_instance, Skill)
    assert skill_instance.id == 1

    # Test entity
    ce = CombatEntity(id=-1, name="Test Entity")

    # Make sure it correctly obtained the Skill with id 1
    assert 1 in ce.skill_controller
    assert ce.skill_controller[1].name == skill_instance.name

    # Make the test Entity obtain xp in the skill
    s: Skill = ce.skill_controller.skills[1]
    s.gain_xp(s.remaining_xp + 1)

    # Check that it leveled up
    assert s.level > 1

    # Generate a simple skill requirement for level 2
    r = SkillRequirement(1, 2)

    assert r.fulfilled(ce)
