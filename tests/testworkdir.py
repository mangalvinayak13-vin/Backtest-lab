from pathlib import Path


# the folder starts empty and can be written to
def testWorkdirIsEmptyAndWritable(workdir: Path) -> None:
    assert list(workdir.iterdir()) == []
    with (workdir / "note.txt").open("w", encoding="utf-8") as file:
        file.write("hello")
    with (workdir / "note.txt").open(encoding="utf-8") as file:
        assert file.read() == "hello"


# every test gets its own folder
def testWorkdirIsDifferentForEachTest(workdir: Path) -> None:
    assert not (workdir / "note.txt").exists()
