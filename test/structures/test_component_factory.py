from game.structures.messages import ComponentFactory


def test_bare_call():
    """
    Test that the ComponentFactory behaves correctly for a trivial call
    """
    result = ComponentFactory.get()
    assert "content" in result
    assert "options" in result
    assert not result["content"]
    assert not result["options"]


def test_content_only():
    """
    Test that ComponentFactory correctly stores the content argument in the returned dict
    """

    lst = ["A", " set of ", "strings"]
    result = ComponentFactory.get(lst)
    assert "content" in result
    assert "options" in result
    assert result["content"]
    assert not result["options"]
    assert result["content"] == lst


def test_content_options():
    """
    Test that ComponentFactory correctly stores both arguments
    """

    lst = ["A", " set of ", "strings"]
    opt = [["one"], ["two"], ["this ", "is ", "three."]]
    result = ComponentFactory.get(lst, opt)
    assert "content" in result
    assert "options" in result
    assert result["content"]
    assert result["content"] == lst
    assert result["options"] == opt
