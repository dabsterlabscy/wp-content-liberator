#!/usr/bin/env python3
"""
PHP brace balance checker for WPConvert themes.

WPConvert-generated functions.php files typically have a non-zero baseline
brace balance — usually (-2, 0, 0) meaning two unclosed parentheses but
balanced brackets and curly braces. This baseline comes from the generator
and is NOT a syntax error.

This script reads the file, walks it with a state machine that ignores
PHP strings, comments, and HTML regions, and reports the balance. It must
match the known baseline before AND after any edit — any change indicates
you introduced a syntax error.

Usage:
    python3 check_balance.py <path-to-functions.php> [expected_parens] [expected_braces] [expected_brackets]

Example:
    python3 check_balance.py functions.php -2 0 0

Exits 0 if balance matches expected, 1 if it differs.
"""

import sys


def check_balance(path, expected_parens=0, expected_braces=0, expected_brackets=0):
    with open(path, 'r', encoding='utf-8') as f:
        code = f.read()

    # State machine states
    state = 'html'  # outside PHP
    bal = {'(': 0, ')': 0, '{': 0, '}': 0, '[': 0, ']': 0}
    i = 0
    n = len(code)

    while i < n:
        c = code[i]
        c2 = code[i:i + 2]

        if state == 'html':
            if c2 == '<?':
                state = 'php'
                i += 2
            else:
                i += 1
            continue

        if state == 'php':
            if c2 == '?>':
                state = 'html'
                i += 2
                continue
            if c2 == '//':
                state = 'line_comment'
                i += 2
                continue
            if c == '#':
                state = 'line_comment'
                i += 1
                continue
            if c2 == '/*':
                state = 'block_comment'
                i += 2
                continue
            if c == "'":
                state = 'single_string'
                i += 1
                continue
            if c == '"':
                state = 'double_string'
                i += 1
                continue
            if c in '(){}[]':
                bal[c] += 1
            i += 1
            continue

        if state in ('single_string', 'double_string'):
            if c == '\\' and i + 1 < n:
                i += 2  # skip escaped char
                continue
            if (state == 'single_string' and c == "'") or (state == 'double_string' and c == '"'):
                state = 'php'
            i += 1
            continue

        if state == 'line_comment':
            if c == '\n':
                state = 'php'
            i += 1
            continue

        if state == 'block_comment':
            if c2 == '*/':
                state = 'php'
                i += 2
                continue
            i += 1
            continue

    actual_parens = bal['('] - bal[')']
    actual_braces = bal['{'] - bal['}']
    actual_brackets = bal['['] - bal[']']

    print(f"{path}: ()={actual_parens} {{}}={actual_braces} []={actual_brackets}")
    print(f"Expected: ()={expected_parens} {{}}={expected_braces} []={expected_brackets}")

    if (actual_parens, actual_braces, actual_brackets) == (expected_parens, expected_braces, expected_brackets):
        print("OK — balance matches expected baseline.")
        return 0
    else:
        delta_p = actual_parens - expected_parens
        delta_c = actual_braces - expected_braces
        delta_b = actual_brackets - expected_brackets
        print(f"MISMATCH — delta: ()={delta_p:+d} {{}}={delta_c:+d} []={delta_b:+d}")
        print("Likely syntax error introduced by recent edit. Review the diff and restore.")
        return 1


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 check_balance.py <path> [expected_parens] [expected_braces] [expected_brackets]")
        sys.exit(2)

    path = sys.argv[1]
    expected_parens = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    expected_braces = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    expected_brackets = int(sys.argv[4]) if len(sys.argv) > 4 else 0

    sys.exit(check_balance(path, expected_parens, expected_braces, expected_brackets))
