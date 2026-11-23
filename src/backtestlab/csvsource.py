import csv
import math
import re
from datetime import date, datetime
from pathlib import Path

from backtestlab.errors import DataError
from backtestlab.prices import PriceData, Row, buildPrices, cleanHeader

REQUIRED = ("date", "open", "high", "low", "close")
NUMBERS = ("open", "high", "low", "close", "volume", "adjclose")
MONTHFORMATS = ("%d-%b-%Y", "%d %b %Y", "%b %d, %Y")
NUMERICDATE = re.compile(r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}")
ADJUSTED = "Prices were adjusted for dividends and splits using the Adj Close column."


# read every line of the file as a list of cells
def readTable(path: Path) -> list[list[str]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as file:
            return list(csv.reader(file))
    except FileNotFoundError:
        raise DataError(f"The file {path} was not found. Check the path.") from None
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        raise DataError(
            f"The file {path} could not be read as a UTF-8 CSV file ({error})."
        ) from error


# the date in an ISO text such as 2024-01-31, or None
def tryIso(text: str) -> datetime | None:
    try:
        day = date.fromisoformat(text)
    except ValueError:
        return None
    return datetime(day.year, day.month, day.day)


# the date in the text for one format, or None when it does not fit
def tryFormat(text: str, dateFormat: str) -> datetime | None:
    try:
        return datetime.strptime(text, dateFormat)
    except ValueError:
        return None


# the message for a date that could not be read
def dateMessage(text: str, number: int, dateFormat: str | None) -> str:
    start = f"Line {number}: the date '{text}'"
    if dateFormat is not None:
        return f"{start} does not match the date format {dateFormat}."
    if NUMERICDATE.fullmatch(text):
        return (
            f"{start} could mean two different days (1 February or 2 January?). "
            "Pass --date-format (dateFormat in Python), for example %d/%m/%Y."
        )
    return (
        f"{start} could not be read. Use dates like 2024-01-31 or 31-Jan-2024, "
        "or pass --date-format (dateFormat in Python)."
    )


# turn the text of a date cell into a date without a time zone
def parseDate(text: str, number: int, dateFormat: str | None) -> datetime:
    text = text.strip()
    if dateFormat is not None:
        guesses = [tryFormat(text, dateFormat)]
    else:
        guesses = [tryIso(text)] + [tryFormat(text, form) for form in MONTHFORMATS]
    for guess in guesses:
        if guess is not None:
            return guess
    raise DataError(dateMessage(text, number, dateFormat))


# turn the text of a number cell into a float, with nan for an empty cell
def parseNumber(text: str, number: int, name: str) -> float:
    cleaned = text.strip().replace(",", "")
    if cleaned == "":
        return math.nan
    try:
        return float(cleaned)
    except ValueError:
        raise DataError(
            f"Line {number}: '{text.strip()}' in the {name} column is not a number."
        ) from None


# the number to multiply the prices of a row by to adjust them
def adjustFactor(close: float, adjclose: float, number: int) -> float:
    if math.isnan(close) or close <= 0:
        return 1.0
    if math.isnan(adjclose):
        raise DataError(f"Line {number}: the Adj Close value is missing.")
    return adjclose / close


# the cell at a position, or an empty text when the line is too short
def cellAt(cells: list[str], position: int) -> str:
    return cells[position] if position < len(cells) else ""


# the position of each known column in the header line
def findColumns(header: list[str]) -> dict[str, int]:
    columns: dict[str, int] = {}
    for position, name in enumerate(header):
        columns.setdefault(cleanHeader(name), position)
    missing = [name for name in REQUIRED if name not in columns]
    if missing:
        found = ", ".join(name.strip() for name in header)
        raise DataError(
            f"The file has no {', '.join(missing)} column. The columns found were: {found}."
        )
    return columns


# one line of the file as a row of prices
def makeRow(cells: list[str], columns: dict[str, int], number: int, dateFormat: str | None) -> Row:
    day = parseDate(cellAt(cells, columns["date"]), number, dateFormat)
    values = {
        name: parseNumber(cellAt(cells, columns[name]), number, name)
        for name in NUMBERS
        if name in columns
    }
    factor = 1.0
    if "adjclose" in values:
        factor = adjustFactor(values["close"], values["adjclose"], number)
    return Row(
        day,
        values["open"] * factor,
        values["high"] * factor,
        values["low"] * factor,
        values["close"] * factor,
        values.get("volume", math.nan),
    )


# load daily prices from a CSV file, and check and clean them
def loadCsv(path: str | Path, dateFormat: str | None = None) -> PriceData:
    location = Path(path)
    table = readTable(location)
    lines = [
        (number, cells)
        for number, cells in enumerate(table, start=1)
        if any(cell.strip() for cell in cells)
    ]
    if not lines:
        raise DataError(f"The file {location} is empty.")
    columns = findColumns(lines[0][1])
    notes = [ADJUSTED] if "adjclose" in columns else []
    rows = [makeRow(cells, columns, number, dateFormat) for number, cells in lines[1:]]
    source = str(location).replace("\\", "/")
    return buildPrices(rows, "volume" in columns, source, notes)


# save prices to a CSV file that loadCsv can read back exactly
def saveCsv(prices: PriceData, path: str | Path) -> None:
    target = Path(path)
    if not target.parent.exists():
        target.parent.mkdir(parents=True)
    frame = prices.frame
    columns = list(frame.columns)
    with target.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(["date", *columns])
        for stamp, values in zip(frame.index, frame.values, strict=True):
            cells = ["" if math.isnan(float(value)) else repr(float(value)) for value in values]
            writer.writerow([stamp.date().isoformat(), *cells])
