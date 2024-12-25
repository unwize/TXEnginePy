class CompoundError(Exception):
    """
    A generic error in which additional errors can be embedded and will be raised.
    """

    def __init__(self, message: str, errors: dict[type[Exception], str] = None):
        super().__init__(message)

        if errors:
            for error in errors:
                raise error(str)


class InputValidationError(CompoundError):
    """
    An error that is thrown when input to a StateDevice is invalid.
    """


class StateDeviceInternalError(CompoundError):
    """
    An error that is thrown when a StateDevice's internal logic fails
    """

    pass


class CombatError(CompoundError):
    """
    A generic error thrown when there is a problem executing combat logic
    """

    pass


class CombatHandlerError(CompoundError):
    """
    An error that is thrown when a PhaseHandler object has a problem executing logic
    """

    pass
