# parse_dat.py
import re
from models import NetEntry

_DELIM_RE = re.compile(r"^-{5,}\s*$", re.MULTILINE)

def split_dat_entries(text: str) -> list[str]:
    return [b for b in _DELIM_RE.split(text) if b.strip()]

def parse_dat_entry(block: str) -> dict:
    """
    Returns a dict keyed by field name, plus 'entry_index' and 'header'.
    We return a dict rather than a NetEntry so the caller can merge with the ado-derived entry.
    """
    out = {"entry_index": None, "simplig": {}}
    header_m = re.match(r"^\s*(\d+):(.+?)/intercluster bonds for rings>(\d+)", block)
    if header_m:
        out["entry_index"] = int(header_m.group(1))
        out["title_formula"] = header_m.group(2).strip()
        out["rings_threshold"] = int(header_m.group(3))

    def grab(pattern, cast=str):
        m = re.search(pattern, block, re.MULTILINE)
        if not m:
            return None
        try:
            return cast(m.group(1).strip())
        except (ValueError, TypeError):
            return None

    out["space_group"] = grab(r"^Space Group:\s*([^;]+);")
    out["crystal_class"] = grab(r"^Crystal Class:\s*(\S+)")
    out["pearson_symbol"] = grab(r"^Pearson Symbol:\s*(\S+)")
    out["z_value"] = grab(r"^Z=\s*(\d+)", int)

    # Cell parameters: "A=  9.8064  B= 10.6685  C= 13.9712"
    abc = re.search(r"^A=\s*([\d.]+)\s+B=\s*([\d.]+)\s+C=\s*([\d.]+)", block, re.MULTILINE)
    if abc:
        out["cell_a"], out["cell_b"], out["cell_c"] = map(float, abc.groups())
    ang = re.search(r"^Alpha=\s*([\d.]+)\s+Beta=\s*([\d.]+)\s+Gamma=\s*([\d.]+)", block, re.MULTILINE)
    if ang:
        out["cell_alpha"], out["cell_beta"], out["cell_gamma"] = map(float, ang.groups())
    vol = re.search(r"^Volume=\s*([\d.]+)", block, re.MULTILINE)
    if vol:
        out["cell_volume"] = float(vol.group(1))

    out["centat"] = grab(r"^CENTAT:\s*(.+?)$")

    # SIMPLIG: "SIMPLIG: ZA=C4O10Zn4 ZB=C6 ZC=C8O2"
    simplig_line = re.search(r"^SIMPLIG:\s*(.+?)$", block, re.MULTILINE)
    if simplig_line:
        for pair in simplig_line.group(1).split():
            if "=" in pair:
                k, v = pair.split("=", 1)
                out["simplig"][k] = v

    # Comment: "File: ABUWOJ_clean_pacman.cif."
    file_m = re.search(r"File:\s*(\S+?\.cif)", block)
    if file_m:
        out["cif_filename"] = file_m.group(1)
        # CCDC/CSD refcodes are 6 letters, sometimes 6 letters + digits. Take leading alpha chunk.
        refcode_m = re.match(r"^([A-Z]{6}\d{0,2})", file_m.group(1))
        if refcode_m:
            out["refcode"] = refcode_m.group(1)

    return out