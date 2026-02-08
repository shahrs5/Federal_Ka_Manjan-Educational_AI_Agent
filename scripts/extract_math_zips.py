#!/usr/bin/env python3
"""
Extract main.tex from each Math zip file into an Extracted/ directory.

Usage:
    python scripts/extract_math_zips.py

Each zip contains a single main.tex.  This script renames it to match
the zip filename (e.g. "Class 9 Math - Chapter 4 (Exercise 4.5).tex")
and places it in  Notes/Class {X}/Math/Content/Extracted/.

Skips:
- Files that already exist in the output directory.
- The top-level Notes/Math/ directory (it duplicates Notes/Class X/Math/).
"""
import sys
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
NOTES_DIR = BASE_DIR / "Notes"


def extract_for_class(class_level: int) -> int:
    content_dir = NOTES_DIR / f"Class {class_level}" / "Math" / "Content"
    if not content_dir.exists():
        print(f"  [skip] {content_dir} does not exist")
        return 0

    out_dir = content_dir / "Extracted"
    out_dir.mkdir(exist_ok=True)

    zips = sorted(content_dir.glob("*.zip"))
    print(f"  Found {len(zips)} zip files in {content_dir}")

    extracted = 0
    for zp in zips:
        tex_name = zp.stem + ".tex"
        dest = out_dir / tex_name

        if dest.exists():
            print(f"    [exists] {tex_name}")
            continue

        try:
            with zipfile.ZipFile(zp, "r") as zf:
                # Find main.tex (or the first .tex file)
                tex_files = [n for n in zf.namelist() if n.endswith(".tex")]
                if not tex_files:
                    print(f"    [warn] No .tex in {zp.name}")
                    continue

                src_name = "main.tex" if "main.tex" in tex_files else tex_files[0]
                dest.write_bytes(zf.read(src_name))
                extracted += 1
                print(f"    [ok] {tex_name}")
        except Exception as e:
            print(f"    [error] {zp.name}: {e}")

    return extracted


def main():
    total = 0
    for cl in (9, 10):
        print(f"\n--- Class {cl} ---")
        total += extract_for_class(cl)
    print(f"\nDone. Extracted {total} new .tex files.")


if __name__ == "__main__":
    main()
