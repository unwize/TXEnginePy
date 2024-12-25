from game.cache import from_cache, get_cache, cache_element, delete_element


def test_get_cache():
    """
    Test that the cache object can be retrieved
    """
    assert type(get_cache()) is dict


def test_from_cache():
    """
    Test that 'from_cache' can retrieve elements stored in the cache
    """
    cache = get_cache()
    cache["element"] = 1

    assert from_cache("element") == 1

    cache["root"] = {"branch": "leaf"}

    assert from_cache("root.branch") == "leaf"


def test_delete_element():
    """
    Test that elements can be deleted from the cache correctly
    """
    cache = get_cache()
    cache["element"] = 1

    assert from_cache("element") == 1
    delete_element("element")
    assert from_cache("element") is None

    cache["root"] = {"branch": "leaf"}
    assert from_cache("root.branch") == "leaf"

    delete_element("root.branch")
    assert from_cache("root.branch") is None


def test_cache_element():
    """
    Test that 'cache_element' can correctly store elements in the cache
    """
    delete_element("num")
    delete_element("root.branch")
    delete_element("element")

    # Trivial case
    assert from_cache("num") is None
    cache_element("num", 1)
    assert from_cache("num") == 1

    # recursively cached
    assert from_cache("root.branch") is None
    cache_element("root.branch", "leaf")
    assert from_cache("root.branch") == "leaf"
