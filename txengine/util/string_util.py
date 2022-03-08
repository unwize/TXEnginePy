def o_tag(prop: [str, list[str]]) -> str:
    """Generate a Rich opening tag for each string and return as a string

    See https://rich.readthedocs.io/en/stable/introduction.html
    """
    if type(prop) == list:
        s = ""
        for p in prop:
            s = s + "[{}]".format(p)

    return "[{}]".format(prop)


def c_tag(prop: [str, list[str]]) -> str:
    """Generate a Rich closing tag for each string and return as a string

    See https://rich.readthedocs.io/en/stable/introduction.html
    """
    if type(prop) == list:
        s = ""
        for p in prop:
            s = s + "[/{}]".format(p)

    return "[/{}]".format(prop)
