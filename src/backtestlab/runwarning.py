from dataclasses import dataclass


# a warning with a short code and a message in plain words
@dataclass(frozen=True)
class RunWarning:
    code: str
    message: str
