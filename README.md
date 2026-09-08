# rokugpx-parity-tools

Locale key-parity checker used by RokuGPX CI (iOS `ja.json`/`en.json`, Android `values`/`values-en`).
Single-purpose, no ledgers, no secrets. Canonical home of `key_parity.py` — do not copy it into app repos.

## Usage

```sh
# nested JSON locales
python3 key_parity.py --format json locales/ja.json locales/en.json --label ja en

# Android string resources
python3 key_parity.py --format android-xml \
    app/src/main/res/values/strings.xml \
    app/src/main/res/values-en/strings.xml --label ja en
```

Exit codes: `0` key sets match · `1` at least one key missing (each one is named) ·
`2` bad arguments or unreadable input.

Nothing is written; the two files are only read.

## Why a separate check

A missing key is a different failure from a wrong translation, and comparing values will not
find it — there is no value to compare. Both platforms fail quietly in their own way:

- A nested-JSON lookup that returns the key when the key is absent renders the raw key on
  screen (`screen.title` where a label should be).
- Android resource lookup falls back to the default `values/` folder, so an English build
  silently shows the default-language string.

Neither shows up in a review of the strings that *are* there. You have to compare the key sets.

## What it does not do

1. **It does not judge values.** Two files can have identical key sets and still be mistranslated.
2. **It cannot see a key that should exist but is in neither file.** If code builds a lookup key
   by string interpolation, a key it needs may be absent from every locale file and the key sets
   still match — this tool reports zero. That class of gap is only visible by counting from the
   call sites, not from the files.
3. **An empty value counts as present.**
4. **It reads only the two files given.** Other locales are not consulted.

Limit 2 is the one that has actually bitten us, so it is stated first in the tool's own docstring
as well.

## Tests

```sh
./tests/run.sh
```

The fixtures are synthetic. The tests deliberately break input and require the tool to fail on
exactly that input: a checker that always returned `0`, or one that always returned `1`, would
each pass some of these and fail the rest. The test that separates a working checker from those
two is the one that breaks the JSON fixture and then asserts the **XML** run is still clean.

## Using it from CI

Check the app repo and this repo out side by side, then run one line. This repo is public, so no
token is needed for the checkout.

```yaml
- uses: actions/checkout@v4
  with: { path: app }
- uses: actions/checkout@v4
  with: { repository: Hue166/rokugpx-parity-tools, path: parity-tools }
- uses: actions/setup-python@v5
  with: { python-version: '3.12' }
- run: |
    python3 parity-tools/key_parity.py --format json \
      app/<path-to>/ja.json app/<path-to>/en.json --label ja en
```
