# composition.py
import re
from collections import Counter

_TOKEN_RE = re.compile(r"([A-Z][a-z]?)(\d*)|(\()|(\))(\d*)")

def parse_formula(formula: str) -> dict[str, int]:
    """
    Parse 'CoH8C12(NO2)2' -> {'Co':1, 'H':8, 'C':12, 'N':2, 'O':4}.
    Limitations: no nested parens beyond one level tested; no hydrates with dots; no charges.
    Returns empty dict on unparseable input rather than raising.
    """
    stack: list[Counter] = [Counter()]
    i = 0
    try:
        while i < len(formula):
            ch = formula[i]
            if ch == "(":
                stack.append(Counter())
                i += 1
            elif ch == ")":
                i += 1
                num_match = re.match(r"\d+", formula[i:])
                mult = int(num_match.group()) if num_match else 1
                if num_match:
                    i += len(num_match.group())
                top = stack.pop()
                for el, n in top.items():
                    stack[-1][el] += n * mult
            elif ch.isupper():
                el_match = re.match(r"[A-Z][a-z]?", formula[i:])
                el = el_match.group()
                i += len(el)
                num_match = re.match(r"\d+", formula[i:])
                n = int(num_match.group()) if num_match else 1
                if num_match:
                    i += len(num_match.group())
                stack[-1][el] += n
            else:
                # Unexpected char (e.g., in malformed titles); skip defensively.
                i += 1
        return dict(stack[0]) if len(stack) == 1 else {}
    except Exception:
        return {}