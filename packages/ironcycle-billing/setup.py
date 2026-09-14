from pathlib import Path
from setuptools import setup

root = Path(__file__).resolve().parent
flutter_root = root / "flutter" / "ironcycle_billing"
data_files = []

for path in sorted(flutter_root.rglob("*")):
    if path.is_file():
        destination = path.parent.relative_to(root).as_posix()
        source = path.relative_to(root).as_posix()
        data_files.append((destination, [source]))

setup(data_files=data_files)
