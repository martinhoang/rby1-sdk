#!/usr/bin/env python3
"""
Fixes MuJoCo 3.8+ "file already included" errors by detecting duplicate
<include file="..."/> entries in an XML file and replacing each duplicate
occurrence (2nd, 3rd, …) with a copy of the file given a unique suffix.

Usage:
    python3 dedup_includes.py <xml_file> [<xml_file> ...]
    python3 dedup_includes.py rby1.xml rby1_v1.0.xml rby1_v1.1.xml rby1_v1.2.xml
"""

import os
import re
import shutil
import sys


def dedup_includes(xml_path: str) -> int:
    xml_dir = os.path.dirname(os.path.abspath(xml_path))
    with open(xml_path, "r") as f:
        lines = f.readlines()

    # Track how many times each resolved path has been seen
    seen: dict[str, int] = {}
    # Map original relative path → list of replacement paths (index = occurrence - 1)
    replacements: dict[str, list[str]] = {}
    new_lines = []
    changed = 0

    for line in lines:
        m = re.search(r'<include\s+file="([^"]+)"', line)
        if m:
            rel = m.group(1)
            # Normalise: strip leading ./
            norm = rel.lstrip("./") if rel.startswith("./") else rel
            abs_src = os.path.join(xml_dir, norm)

            seen[norm] = seen.get(norm, 0) + 1
            occurrence = seen[norm]

            if occurrence > 1:
                # Build a unique copy path: foo/geoms.xml → foo/geoms_2.xml
                base, ext = os.path.splitext(norm)
                copy_rel = f"{base}_{occurrence}{ext}"
                abs_copy = os.path.join(xml_dir, copy_rel)

                if not os.path.exists(abs_copy):
                    shutil.copy2(abs_src, abs_copy)
                    print(f"  Created copy: {copy_rel}")

                # Reconstruct the include line preserving indentation / quoting style
                # Replace just the file attribute value
                new_rel = "./" + copy_rel if rel.startswith("./") else copy_rel
                line = re.sub(
                    r'(<include\s+file=")[^"]+(")',
                    lambda _m: f'{_m.group(1)}{new_rel}{_m.group(2)}',
                    line,
                    count=1,
                )
                changed += 1
                print(f"  Line {len(new_lines)+1}: {rel!r} → {new_rel!r} (occurrence {occurrence})")

        new_lines.append(line)

    if changed:
        with open(xml_path, "w") as f:
            f.writelines(new_lines)
        print(f"  Wrote {xml_path}  ({changed} include(s) fixed)")
    else:
        print(f"  No duplicates in {xml_path}")

    return changed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    total = 0
    for path in sys.argv[1:]:
        print(f"\nProcessing: {path}")
        total += dedup_includes(path)

    print(f"\nDone — {total} duplicate include(s) fixed across {len(sys.argv)-1} file(s).")
