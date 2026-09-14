from pathlib import Path
from setuptools import setup
root = Path(__file__).parent
files = []
for path in (root / "flutter" / "ironcycle_billing").rglob("*"):
    if path.is_file():
        target = str(path.parent.relative_to(root))
        files.append((target, [str(path)]))
setup(data_files=files)
