import weakref

from .enums import InputType, is_valid_range
from .messages import StringContent, Frame


class StateDevice:

    def __init__(self, input_type: InputType, input_range: dict[str, any] = None) -> None:
        self.str_buffer: list[StringContent] = []
        self.input_type: InputType = input_type
        self.input_range: dict[str: any] = input_range or {"upper_limit": None,
                                                           "lower_limit": None,
                                                           "length": None
                                                           }
        self.__engine = None

    @property
    def engine(self):
        return self.__engine

    @engine.setter
    def engine(self, engine) -> None:
        self.__engine = weakref.ref(engine)

    @property
    def val(self) -> list[StringContent]:
        return self.str_buffer

    @property
    def domain_lower_limit(self) -> any:
        return self.input_range["lower_limit"]

    @domain_lower_limit.setter
    def domain_lower_limit(self, val: any) -> None:
        if is_valid_range(self.input_type,
                          lower_limit=val,
                          upper_limit=self.domain_upper_limit,
                          length=self.domain_length):
            self.input_range["lower_limit"] = val
        else:
            raise ValueError(f"Tried to set lower limit of {self.input_type} to value of type {type(val)}!")

    @property
    def domain_upper_limit(self) -> any:
        return self.input_range["upper_limit"]

    @domain_upper_limit.setter
    def domain_upper_limit(self, val: any) -> None:
        if is_valid_range(self.input_type,
                          lower_limit=self.domain_lower_limit,
                          upper_limit=val,
                          length=self.domain_length):
            self.input_range["lower_limit"] = val
        else:
            raise ValueError(f"Tried to set lower limit of {self.input_type} to value of type {type(val)}!")

    @property
    def domain_length(self) -> [int, None]:
        return self.input_range["length"]

    @domain_length.setter
    def domain_length(self, val: [int, None]) -> None:
        if is_valid_range(self.input_type,
                          lower_limit=self.domain_lower_limit,
                          upper_limit=self.domain_upper_limit,
                          length=self.domain_length):
            self.input_range["lower_limit"] = val
        else:
            raise ValueError(f"Tried to set lower limit of {self.input_type} to value of type {type(val)}!")

    @property
    def input_domain(self) -> dict[str, any]:
        return self.input_range

    @input_domain.setter
    def input_domain(self, input_type: InputType, upper_limit=None, lower_limit=None, length=None) -> None:
        if not is_valid_range(input_type, upper_limit, lower_limit, length):
            raise ValueError(f"""Invalid input domain values for type {input_type}:\n 
                                                                       lower_limit: {lower_limit}\n
                                                                       upper_limit: {upper_limit}\n
                                                                       length: {length}
                              """)

    @property
    def components(self) -> dict[str, any]:
        # raise NotImplementedError  # TODO: Uncomment
        pass

    def to_frame(self) -> Frame:
        return Frame(self.components, self.input_type, self.input_range, self.__class__.__name__)
