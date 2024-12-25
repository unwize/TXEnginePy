from game.structures.messages import StringContent


def test_trivial_init():
    sc = StringContent(value="A String")
    assert sc.value == "A String"


def test_form_list_init():
    sc = StringContent(value="A Formatted String", formatting=["Stylish"])
    assert sc.value == "A Formatted String"
    assert type(sc.formatting) is list
    assert len(sc.formatting) == 1
    assert sc.formatting[0] == "Stylish"
