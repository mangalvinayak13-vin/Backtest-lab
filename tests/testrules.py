import ast
import io
import re
import subprocess
import tokenize
from pathlib import Path

import pytest

LOWLINE = "\N{LOW LINE}"
PRAGMA = re.compile(r"#\s*(type:\s*ignore|noqa|pragma:\s*no\s*cover|fmt:\s*(off|skip))")
BINARY = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf"}


# the names of the files git would include, skipping ignored and locally excluded ones
def listNames(root: Path) -> list[str]:
    command = ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"]
    result = subprocess.run(command, cwd=root, stdout=subprocess.PIPE, text=True, check=True)
    names = [name for name in result.stdout.split("\0") if name]
    return [name for name in names if (root / name).exists()]


# the text of a file, or None for a binary file
def readText(path: Path) -> str | None:
    if path.suffix.lower() in BINARY:
        return None
    try:
        with path.open(encoding="utf-8") as file:
            return file.read()
    except UnicodeDecodeError:
        return None


# every python file as a name and its text
def pythonFiles(root: Path) -> list[tuple[str, str]]:
    found = []
    for name in listNames(root):
        text = readText(root / name)
        if name.endswith(".py") and text is not None:
            found.append((name, text))
    return found


# a statement that is just a string, which is what a docstring is
def startsWithString(statement: ast.stmt) -> bool:
    if not isinstance(statement, ast.Expr):
        return False
    return isinstance(statement.value, ast.Constant) and isinstance(statement.value.value, str)


# the line numbers of every docstring in one python file
def docstringLines(text: str) -> list[int]:
    lines = []
    for node in ast.walk(ast.parse(text)):
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        first = node.body[0] if node.body else None
        if first is not None and startsWithString(first):
            lines.append(first.lineno)
    return lines


# the line numbers of every comment that silences a tool
def pragmaLines(text: str) -> list[int]:
    lines = []
    for token in tokenize.tokenize(io.BytesIO(text.encode("utf-8")).readline):
        if token.type == tokenize.COMMENT and PRAGMA.search(token.string):
            lines.append(token.start[0])
    return lines


# no file name and no line of text contains the forbidden character
def testNoUnderscoresInNamesOrText(pytestconfig: pytest.Config) -> None:
    root = pytestconfig.rootpath
    problems = []
    for name in listNames(root):
        if LOWLINE in name:
            problems.append(f"{name}: the file name has an underscore")
        text = readText(root / name) or ""
        for number, line in enumerate(text.splitlines(), start=1):
            if LOWLINE in line:
                problems.append(f"{name}:{number}: the text has an underscore")
    assert problems == []


# no module, class or function starts with a docstring
def testNoDocstrings(pytestconfig: pytest.Config) -> None:
    problems = []
    for name, text in pythonFiles(pytestconfig.rootpath):
        for number in docstringLines(text):
            problems.append(f"{name}:{number}: docstring")
    assert problems == []


# nothing silences ruff, mypy, coverage or the formatter with a comment
def testNoToolPragmas(pytestconfig: pytest.Config) -> None:
    problems = []
    for name, text in pythonFiles(pytestconfig.rootpath):
        for number in pragmaLines(text):
            problems.append(f"{name}:{number}: tool pragma")
    assert problems == []


# the checks above really do catch what they are meant to catch
def testTheCheckersFindBadCode() -> None:
    assert docstringLines('def f() -> None:\n    "doc"\n') == [2]
    assert docstringLines("x = 1\n") == []
    assert pragmaLines("x = 1  # noqa\n") == [1]
    assert pragmaLines("x = 'noqa'\n") == []
