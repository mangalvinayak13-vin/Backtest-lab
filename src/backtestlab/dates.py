from datetime import date

from backtestlab.errors import SettingsError


# turn the text of a date into a date, or stop with a clear message
def parseDay(text: str, name: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise SettingsError(f"The {name} date '{text}' is not a date like 2024-01-31.") from None
