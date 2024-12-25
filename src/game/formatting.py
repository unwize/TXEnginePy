from loguru import logger

supported_style_arguments = set()
formatting: dict[str, list[str]] = {}


def register_arguments(arguments: list[str]):
    """
    Register a string as a supported styling argument

    Args:
        arguments: The string to register

    Returns: None

    """
    global supported_style_arguments

    for arg in arguments:
        if type(arg) is str:
            if arg in supported_style_arguments:
                logger.warning(f"[formatting.py] Registering duplicate argument: {arg}")
            else:
                supported_style_arguments.add(arg)
        else:
            logger.warning(f"Cannot register argument of type {type(arg)}!")


def register_style(style_name: str, style_args: list[str]) -> None:
    """
    Register a style in the global style cache

    Args:
        style_name: name of the style
        style_args: style arguments. These must be supported (registered in supported_style_arguments)

    Returns: None

    """
    global formatting

    if type(style_name) is not str or len(style_name) < 2:
        raise TypeError(f"style_name must be a str! Got {type(style_name)} instead.")

    if len(style_args) < 1:
        raise ValueError(f"Cannot add a style with zero arguments for style {style_name}!")

    if style_name in formatting:
        raise ValueError(f"Cannot register duplicate style_name for {style_name}!")

    for arg in style_args:
        if arg not in supported_style_arguments:
            raise ValueError(f"Unknown argument {arg} for style {style_name}!")

    formatting[style_name] = style_args


def get_style(style_name: str) -> list[str]:
    """
    Look up a style and return its arguments
    Args:
        style_name: The style to look up

    Returns: A list of style arguments

    """
    global formatting

    if style_name not in formatting:
        raise ValueError(f"Cannot locate style {style_name}")

    return list(formatting[style_name])
