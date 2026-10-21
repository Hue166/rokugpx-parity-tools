#!/usr/bin/env python3
"""Locale key-parity checker.

Compares two locale files and reports keys present in one but not the other.
Exits 1 if any key is missing, so CI fails on drift.

    key_parity.py --format json        base.json  other.json
    key_parity.py --format android-xml values/strings.xml values-en/strings.xml

Why this is worth its own check
-------------------------------
A missing key is a different failure from a wrong translation, and neither a
diff of the two files nor a review of the values will surface it reliably:

  * A nested JSON locale read by a lookup that returns the key itself when the
    key is absent will render the raw key on screen ("screen.title" instead of
    a label). The value comparison sees nothing wrong, because there is no value.
  * Android resource lookup falls back to the default `values/` folder when a
    key is missing from `values-en/`, so an English build silently shows the
    default-language string. Again, nothing to compare.

Both fail *quietly*, and both are invisible to a tool that only reads what the
files contain. You have to compare the key sets.

What this tool does NOT do
--------------------------
1. It does not judge values. Two files can have identical key sets and still be
   mistranslated.
2. It does not know about keys that *should* exist but appear in neither file.
   If code builds a lookup key by string interpolation, a key it needs may be
   absent from every locale file, and the key sets still match. That class of
   gap is only visible by counting from the call sites, not from the files.
3. It treats a key with an empty value as present.
4. It reads only the two files given. Other locales are not consulted.
"""
import argparse
import json
import sys
import xml.etree.ElementTree as ET


def load_json(path):
    """Flatten a nested JSON object into dotted keys."""
    def flatten(obj, prefix=()):
        out = {}
        for k, v in obj.items():
            if isinstance(v, dict):
                out.update(flatten(v, prefix + (k,)))
            else:
                out[".".join(prefix + (k,))] = v
        return out

    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be an object")
    return flatten(data)


def load_android_xml(path):
    """Read <string name="..."> entries from an Android string resource file."""
    root = ET.parse(path).getroot()
    out = {}
    for el in root.findall("string"):
        name = el.get("name")
        if name is None:
            continue
        out[name] = "".join(el.itertext())
    return out


LOADERS = {"json": load_json, "android-xml": load_android_xml}


PLURAL_SUFFIXES = ("_one", "_other")


def covered_by_base(key, keys):
    """X_one / X_other is covered when `keys` has the base key X.

    English splits a count string into plural forms; Japanese has one form and
    keeps only X. A plural key whose base is absent is still reported.
    """
    for suffix in PLURAL_SUFFIXES:
        if key.endswith(suffix) and key[: -len(suffix)] in keys:
            return True
    return False


def compare(base, other):
    def missing(src, dst):
        return sorted(k for k in set(src) - set(dst) if not covered_by_base(k, dst))
    return missing(base, other), missing(other, base)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Compare the key sets of two locale files.")
    ap.add_argument("--format", choices=sorted(LOADERS), required=True)
    ap.add_argument("base", help="reference locale file")
    ap.add_argument("other", help="locale file that must have the same keys")
    ap.add_argument("--label", nargs=2, metavar=("BASE", "OTHER"), default=("base", "other"),
                    help="names used in the report (e.g. ja en)")
    a = ap.parse_args(argv)

    load = LOADERS[a.format]
    try:
        base, other = load(a.base), load(a.other)
    except Exception as e:                      # noqa: BLE001 - report and fail loudly
        print(f"could not read locale files: {e}", file=sys.stderr)
        return 2

    bname, oname = a.label
    missing_in_other, missing_in_base = compare(base, other)

    print(f"{bname}: {len(base)} keys")
    print(f"{oname}: {len(other)} keys")
    for k in missing_in_other:
        print(f"MISSING in {oname}: {k}")
    for k in missing_in_base:
        print(f"MISSING in {bname}: {k}")

    total = len(missing_in_other) + len(missing_in_base)
    if total:
        print(f"\n{total} key(s) missing.", file=sys.stderr)
        return 1
    print("\nkey sets match.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
