# parse_ado.py
import re
from models import Sublattice, NetEntry

_HEADER_RE = re.compile(r"^(\d+):(.+?)/intercluster bonds for rings>(\d+)\s*$")
_CUM_RE = re.compile(r"^Cum\s+([\d\s]+)$")
_NUM_RE = re.compile(r"^Num\s+([\d\s]+)$")
_PS_RE = re.compile(r"^(Z[A-Z]\d+)\s+Point symbol:\s*(\S+)")
_EPS_RE = re.compile(r"^(Z[A-Z]\d+)\s+Extended point symbol:\s*(\S+)")
_NET_PS_RE = re.compile(r"^Point symbol for net:\s*(\S+)")
_TD10_RE = re.compile(r"^TD10=(\d+)")
_TOPO_RE = re.compile(r"^Topological type:\s*([^;]+);")
_INTERPEN_RE = re.compile(r"^Totally\s+\d+.*interpenetrating nets")

def split_ado_entries(text: str) -> list[str]:
    """
    Entries are separated by lines of hashes. The structure is:
        ###...###
        N:header
        ###...###
        <body>
        ###...###
        M:next_header
        ###...###
        <body>
    So we split on lines of 2+ hashes and then stitch header+body pairs.
    """
    blocks = [b for b in re.split(r"^#{2,}\s*$", text, flags=re.MULTILINE) if b.strip()]
    entries = []
    i = 0
    while i < len(blocks):
        header_block = blocks[i].strip()
        body_block = blocks[i + 1] if i + 1 < len(blocks) else ""
        # header_block should be a single line like "3:ZnH17..."
        entries.append(f"{header_block}\n{body_block}")
        i += 2
    return entries

def parse_ado_entry(block: str) -> NetEntry:
    lines = block.splitlines()
    header_line = lines[0].strip()
    m = _HEADER_RE.match(header_line)
    if not m:
        # very defensive: malformed header
        return NetEntry(entry_index=-1, header=header_line, title_formula="",
                        parse_error=f"unparseable header: {header_line}")

    entry = NetEntry(
        entry_index=int(m.group(1)),
        header=header_line,
        title_formula=m.group(2).strip(),
        rings_threshold=int(m.group(3)),
    )

    # Walk lines, buffering per-sublattice data.
    current_sub_name = None
    pending = {}  # sub_name -> {"num": [...], "cum": [...], "ps": str, "eps": str}

    for idx, line in enumerate(lines):
        s = line.rstrip()
        if s.startswith("3D framework"):
            entry.is_framework = True
        elif _INTERPEN_RE.match(s):
            entry.interpenetration = s.strip()
        elif _TD10_RE.match(s):
            entry.td10 = int(_TD10_RE.match(s).group(1))
        elif _NET_PS_RE.match(s):
            entry.net_point_symbol = _NET_PS_RE.match(s).group(1)
        elif _TOPO_RE.match(s):
            entry.topological_type = _TOPO_RE.match(s).group(1).strip()

        # Sublattice header line: "ZA1:  1  2  3 ..." — the header just names the sublattice.
        sub_header = re.match(r"^(Z[A-Z]\d+):\s+\d", s)
        if sub_header:
            current_sub_name = sub_header.group(1)
            pending.setdefault(current_sub_name, {})

        if current_sub_name:
            num_m = _NUM_RE.match(s)
            cum_m = _CUM_RE.match(s)
            if num_m:
                pending[current_sub_name]["num"] = [int(x) for x in num_m.group(1).split()]
            elif cum_m:
                pending[current_sub_name]["cum"] = [int(x) for x in cum_m.group(1).split()]

        ps_m = _PS_RE.match(s)
        eps_m = _EPS_RE.match(s)
        if ps_m:
            pending.setdefault(ps_m.group(1), {})["ps"] = ps_m.group(2)
        if eps_m:
            pending.setdefault(eps_m.group(1), {})["eps"] = eps_m.group(2)

    # Degenerate entry check: PDF sample shows "Error in ..." entries with no coord sequences.
    if not pending and "Error in" in block:
        entry.parse_error = "Error entry in source file"
        return entry

    for name, d in pending.items():
        entry.sublattices.append(Sublattice(
            name=name,
            coordination_numerators=d.get("num", []),
            coordination_sequence=d.get("cum", []),
            point_symbol=d.get("ps"),
            extended_point_symbol=d.get("eps"),
        ))
    entry.sublattices.sort(key=lambda x: x.name)
    return entry