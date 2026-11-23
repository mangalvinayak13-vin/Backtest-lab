from datetime import datetime
from pathlib import Path

import pytest

from backtestlab.csvsource import loadCsv
from backtestlab.errors import DataError

HEADER = "Date,Open,High,Low,Close,Volume"
LINES = [
    "2024-01-01,100,102,99,101,5000",
    "2024-01-02,101,103,100,102,6000",
    "2024-01-03,102,104,101,103,7000",
]


# write a csv file in the work folder and give back its path
def writeFile(workdir: Path, lines: list[str], encoding: str = "utf-8") -> Path:
    path = workdir / "prices.csv"
    with path.open("w", encoding=encoding, newline="") as file:
        file.write("\n".join(lines) + "\n")
    return path


# a normal file loads into a clean table
def testLoadsANormalFile(workdir: Path) -> None:
    data = loadCsv(writeFile(workdir, [HEADER, *LINES]))
    assert len(data.frame) == 3
    assert data.frame.index[0] == datetime(2024, 1, 1)
    assert list(data.frame["close"]) == [101.0, 102.0, 103.0]
    assert list(data.frame["volume"]) == [5000.0, 6000.0, 7000.0]
    assert data.source.endswith("prices.csv")
    assert data.notes == ()


# a text path works as well as a Path
def testAcceptsTextPath(workdir: Path) -> None:
    path = writeFile(workdir, [HEADER, *LINES])
    assert len(loadCsv(str(path)).frame) == 3


# headers can have any case and spaces, and other columns are ignored
def testHeadersAreMatchedLoosely(workdir: Path) -> None:
    lines = [" DATE , open ,HIGH,Low,CLOSE,Other", "2024-01-01,1,2,1,2,x", "2024-01-02,2,3,2,3,y"]
    data = loadCsv(writeFile(workdir, lines))
    assert list(data.frame.columns) == ["open", "high", "low", "close"]


# a byte-order mark from Excel does not break the first header
def testByteOrderMarkIsFine(workdir: Path) -> None:
    data = loadCsv(writeFile(workdir, [HEADER, *LINES], encoding="utf-8-sig"))
    assert len(data.frame) == 3


# thousands separators inside quotes are understood
def testThousandsSeparators(workdir: Path) -> None:
    lines = [HEADER, '2024-01-01,"1,234.50","1,250","1,200","1,240.25","1,000"', *LINES[1:]]
    data = loadCsv(writeFile(workdir, lines))
    assert float(data.frame["open"].iloc[0]) == 1234.5
    assert float(data.frame["volume"].iloc[0]) == 1000.0


# dates with month names are understood in the three styles
@pytest.mark.parametrize("text", ["31-Jan-2024", "31 Jan 2024", "Jan 31, 2024"])
def testMonthNameDates(workdir: Path, text: str) -> None:
    lines = [HEADER, f'"{text}",1,2,1,2,10', '"1 Feb 2024",2,3,2,3,10']
    data = loadCsv(writeFile(workdir, lines))
    assert data.frame.index[0] == datetime(2024, 1, 31)


# a numeric date that could be read two ways is rejected
def testAmbiguousDateIsRejected(workdir: Path) -> None:
    lines = [HEADER, "01/02/2024,1,2,1,2,10", "02/02/2024,2,3,2,3,10"]
    with pytest.raises(DataError, match=r"Line 2.*1 February or 2 January.*--date-format"):
        loadCsv(writeFile(workdir, lines))


# a date format makes a numeric date clear
def testDateFormatMakesNumericDatesWork(workdir: Path) -> None:
    lines = [HEADER, "01/02/2024,1,2,1,2,10", "02/02/2024,2,3,2,3,10"]
    data = loadCsv(writeFile(workdir, lines), dateFormat="%d/%m/%Y")
    assert data.frame.index[0] == datetime(2024, 2, 1)


# a date that does not fit the given format is an error
def testDateFormatMismatch(workdir: Path) -> None:
    lines = [HEADER, "2024-01-01,1,2,1,2,10", "2024-01-02,2,3,2,3,10"]
    with pytest.raises(DataError, match=r"does not match the date format %d/%m/%Y"):
        loadCsv(writeFile(workdir, lines), dateFormat="%d/%m/%Y")


# text that is not a date is an error with the line number
def testUnreadableDate(workdir: Path) -> None:
    lines = [HEADER, "yesterday,1,2,1,2,10", *LINES]
    with pytest.raises(DataError, match=r"Line 2: the date 'yesterday' could not be read"):
        loadCsv(writeFile(workdir, lines))


# a cell that is not a number is an error with the line number
def testTextInsteadOfNumber(workdir: Path) -> None:
    lines = [HEADER, "2024-01-01,abc,2,1,2,10", *LINES]
    with pytest.raises(DataError, match="Line 2: 'abc' in the open column is not a number"):
        loadCsv(writeFile(workdir, lines))


# a missing required column lists the columns that were found
def testMissingColumn(workdir: Path) -> None:
    lines = ["Date,Open,High,Close", "2024-01-01,1,2,2"]
    with pytest.raises(DataError, match=r"no low column.*Date, Open, High, Close"):
        loadCsv(writeFile(workdir, lines))


# a file that is not there is a data error
def testMissingFile(workdir: Path) -> None:
    with pytest.raises(DataError, match="was not found"):
        loadCsv(workdir / "nothing.csv")


# a file with no content is a data error
def testEmptyFile(workdir: Path) -> None:
    with pytest.raises(DataError, match="is empty"):
        loadCsv(writeFile(workdir, ["", " , "]))


# a file that is not text is a data error
def testFileThatIsNotText(workdir: Path) -> None:
    path = workdir / "prices.csv"
    with path.open("wb") as file:
        file.write(b"\xff\xfe\x00\x80\x81")
    with pytest.raises(DataError, match="could not be read"):
        loadCsv(path)


# a folder instead of a file is a data error
def testFolderInsteadOfFile(workdir: Path) -> None:
    with pytest.raises(DataError, match="could not be read"):
        loadCsv(workdir)


# blank lines are skipped and short lines count as missing cells
def testBlankAndShortLines(workdir: Path) -> None:
    lines = [HEADER, "", LINES[0], ",,,,,", LINES[1], "2024-01-04,1,2,1,2"]
    data = loadCsv(writeFile(workdir, lines))
    assert len(data.frame) == 3
    assert data.frame["volume"].isna().iloc[2]


# a row with a date but no prices is dropped with a note
def testPlaceholderRowIsDropped(workdir: Path) -> None:
    lines = [HEADER, LINES[0], "2024-01-02,,,,,", LINES[2]]
    data = loadCsv(writeFile(workdir, lines))
    assert len(data.frame) == 2
    assert "Dropped 1 rows" in data.notes[0]


# newest-first files are sorted
def testNewestFirstFile(workdir: Path) -> None:
    data = loadCsv(writeFile(workdir, [HEADER, *reversed(LINES)]))
    assert data.frame.index[0] == datetime(2024, 1, 1)
    assert "ascending" in data.notes[0]


# an Adj Close column rescales all four prices and then goes away
def testAdjCloseAdjustsPrices(workdir: Path) -> None:
    lines = [
        "Date,Open,High,Low,Close,Adj Close",
        "2024-01-01,100,110,90,100,50",
        "2024-01-02,100,110,90,100,60",
    ]
    data = loadCsv(writeFile(workdir, lines))
    assert list(data.frame["open"]) == [50.0, 60.0]
    assert list(data.frame["high"]) == [55.0, 66.0]
    assert list(data.frame["low"]) == [45.0, 54.0]
    assert list(data.frame["close"]) == [50.0, 60.0]
    assert "adjclose" not in data.frame.columns
    assert data.notes == (
        "Prices were adjusted for dividends and splits using the Adj Close column.",
    )


# a missing Adj Close on a row with prices is an error
def testMissingAdjCloseIsAnError(workdir: Path) -> None:
    lines = [
        "Date,Open,High,Low,Close,Adj Close",
        "2024-01-01,100,110,90,100,",
        "2024-01-02,100,110,90,100,100",
    ]
    with pytest.raises(DataError, match="Line 2: the Adj Close value is missing"):
        loadCsv(writeFile(workdir, lines))


# a bad close on a row with an Adj Close is reported as a bad price
def testBadCloseWithAdjClose(workdir: Path) -> None:
    lines = [
        "Date,Open,High,Low,Close,Adj Close",
        "2024-01-01,100,110,90,0,50",
        "2024-01-02,100,110,90,100,100",
    ]
    with pytest.raises(DataError, match="2024-01-01"):
        loadCsv(writeFile(workdir, lines))
