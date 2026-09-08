#!/usr/bin/env bash
# Sensitivity tests for key_parity.py.
#
# The point of these is not that the tool passes on good input. It is that the
# tool FAILS on input we deliberately broke, and fails only on that input. A
# checker that always returns 0 would satisfy test 1 alone; a checker that
# always returns 1 would satisfy test 2 alone. Tests 3 and 6 are the ones that
# separate a working checker from either of those.
#
#   ./tests/run.sh
set -u

here="$(cd "$(dirname "$0")" && pwd)"
tool="$here/../key_parity.py"
fx="$here/fixtures"
pass=0
fail=0

check() {  # check <name> <expected-exit> <cmd...>
  local name="$1" want="$2"; shift 2
  local out; out="$("$@" 2>&1)"; local got=$?
  if [ "$got" = "$want" ]; then
    printf 'ok   %-58s (exit %s)\n' "$name" "$got"
    pass=$((pass + 1))
  else
    printf 'FAIL %-58s (exit %s, wanted %s)\n%s\n' "$name" "$got" "$want" "$out"
    fail=$((fail + 1))
  fi
}

names() {  # names <expected-substring> <cmd...>
  local want="$1"; shift
  local out; out="$("$@" 2>&1)"
  if printf '%s' "$out" | grep -q -- "$want"; then
    printf 'ok   %-58s\n' "names $want"
    pass=$((pass + 1))
  else
    printf 'FAIL %-58s\n%s\n' "names $want" "$out"
    fail=$((fail + 1))
  fi
}

# 1. Same key sets, different values. Translation is not this tool's business.
check "json: same keys, different values -> pass" 0 \
  python3 "$tool" --format json "$fx/base.json" "$fx/translated.json"

# 2. One key removed. Must fail, and must say which key.
check "json: key removed from other -> fail" 1 \
  python3 "$tool" --format json "$fx/base.json" "$fx/missing_one.json"
names "form.hint" \
  python3 "$tool" --format json "$fx/base.json" "$fx/missing_one.json"

# 3. The discriminating control: the other format is untouched by the broken
#    JSON above. Without this, "fails on test 2" cannot be told apart from
#    "fails on everything".
check "android-xml: unaffected by the broken json -> pass" 0 \
  python3 "$tool" --format android-xml "$fx/base.xml" "$fx/translated.xml"

# 4. Extra key in the other file. Missing keys are reported both directions,
#    because an orphan key in one locale is also drift.
check "json: extra key in other -> fail" 1 \
  python3 "$tool" --format json "$fx/base.json" "$fx/extra_one.json"
names "form.reset" \
  python3 "$tool" --format json "$fx/base.json" "$fx/extra_one.json"

# 5. Same break in the XML loader, so neither format is trusted on the other's
#    behalf.
check "android-xml: key removed from other -> fail" 1 \
  python3 "$tool" --format android-xml "$fx/base.xml" "$fx/missing_one.xml"
names "form_cancel" \
  python3 "$tool" --format android-xml "$fx/base.xml" "$fx/missing_one.xml"

# 6. Nesting is part of the key. Moving a key deeper renames it, and that is
#    drift even though every leaf still exists. This pins the flattening rule so
#    it cannot change quietly.
check "json: restructured nesting -> fail" 1 \
  python3 "$tool" --format json "$fx/base.json" "$fx/restructured.json"
names "form.submit" \
  python3 "$tool" --format json "$fx/base.json" "$fx/restructured.json"

# 7. A key with an empty value counts as present. This is a documented limit,
#    not a feature; it is pinned so that changing it is a deliberate act.
check "json: empty value counts as present -> pass" 0 \
  python3 "$tool" --format json "$fx/base.json" "$fx/translated.json"

# 8. Unreadable input must be loud, not silently "no differences".
check "json: unreadable file -> usage error, not pass" 2 \
  python3 "$tool" --format json "$fx/base.json" "$fx/does-not-exist.json"

printf '\n%s passed, %s failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
