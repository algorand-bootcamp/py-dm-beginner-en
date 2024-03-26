from pathlib import Path


def find_app_spec_file(output_dir: Path) -> str | None:
    for file in output_dir.iterdir():
        if file.is_file() and file.suffixes == [".arc32", ".json"]:
            return file.name
    return None
