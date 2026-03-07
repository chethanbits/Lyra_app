"""
Download Swiss Ephemeris data files (ephe folder) for PyJHora.

Run once from prodbackend:
  python download_ephe.py

This downloads the ephe folder from the official Swiss Ephemeris GitHub repo
(planet + lunar files needed for sunrise, tithi, nakshatra, etc.) and saves to
  prodbackend/ephe/

Then set the path before running the API or preload:
  set SWISSEPH_EPHE_PATH=C:\path\to\prodbackend\ephe
  python preload.py
  uvicorn app:app --host 0.0.0.0 --port 8000

Or on Linux/Mac:
  export SWISSEPH_EPHE_PATH=/path/to/prodbackend/ephe
"""

from __future__ import annotations

import os
import zipfile
import urllib.request
from pathlib import Path

# Official Swiss Ephemeris repo (planet + lunar files)
REPO_ZIP = "https://github.com/aloistr/swisseph/archive/refs/heads/master.zip"
EPHE_SUBFOLDER = "swisseph-master/ephe"


def main() -> None:
    root = Path(__file__).resolve().parent
    ephe_dir = root / "ephe"
    ephe_dir.mkdir(parents=True, exist_ok=True)

    zip_path = root / "swisseph-master.zip"
    print("Downloading Swiss Ephemeris repo (ephe folder)...")
    try:
        urllib.request.urlretrieve(REPO_ZIP, zip_path)
    except Exception as e:
        print(f"Download failed: {e}")
        print("Download manually:")
        print("  1. Open https://github.com/aloistr/swisseph")
        print("  2. Click Code -> Download ZIP")
        print("  3. Unzip and copy the 'ephe' folder into prodbackend/ephe")
        return

    print("Extracting ephe files...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if name.startswith(EPHE_SUBFOLDER + "/") and not name.endswith("/"):
                fname = Path(name).name
                data = zf.read(name)
                (ephe_dir / fname).write_bytes(data)
    zip_path.unlink(missing_ok=True)
    count = len(list(ephe_dir.glob("*.se1")))
    print(f"Done. {count} .se1 files in {ephe_dir}")

    abs_ephe = ephe_dir.resolve()
    print("\nSet this before running the API or preload:")
    if os.name == "nt":
        print(f'  set SWISSEPH_EPHE_PATH={abs_ephe}')
    else:
        print(f'  export SWISSEPH_EPHE_PATH="{abs_ephe}"')


if __name__ == "__main__":
    main()
