from datetime import date

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


# a date written so it can't be misread, such as 2 Jan 2024
def formatDate(day: date) -> str:
    return f"{day.day} {MONTHS[day.month - 1]} {day.year}"


# whole-number text with commas in threes (184,213)
def groupWestern(digits: str) -> str:
    return f"{int(digits):,}"


# whole-number text with the last three digits together and then pairs (1,84,213)
def groupIndian(digits: str) -> str:
    if len(digits) <= 3:
        return digits
    rest, last = digits[:-3], digits[-3:]
    pairs: list[str] = []
    while len(rest) > 2:
        pairs.insert(0, rest[-2:])
        rest = rest[:-2]
    pairs.insert(0, rest)
    return ",".join([*pairs, last])


# money with the currency symbol and grouping, such as ₹1,84,213 or 184,213
def formatMoney(amount: float, symbol: str, grouping: str, decimals: int = 0) -> str:
    text = f"{abs(amount):.{decimals}f}"
    whole, point, fraction = text.partition(".")
    grouped = groupIndian(whole) if grouping == "indian" else groupWestern(whole)
    sign = "-" if float(text) > 0 and amount < 0 else ""
    return f"{sign}{symbol}{grouped}{point}{fraction}"


# a fraction as a percentage, with a plain minus sign and no minus on a zero
def formatPercent(fraction: float, decimals: int = 1) -> str:
    text = f"{fraction * 100:.{decimals}f}"
    if float(text) == 0:
        text = text.lstrip("-")
    return f"{text}%"
