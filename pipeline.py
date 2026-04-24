# pipeline.py
import re
from pathlib import Path
from models import Material, NetEntry
from parse_ado import split_ado_entries, parse_ado_entry
from parse_dat import split_dat_entries, parse_dat_entry
from composition import parse_formula

def infer_database(path: Path) -> str:
    name = path.name
    for tag in ("CoreMOF", "CCDC", "CSD"):
        if tag in name:
            return tag
    return "unknown"

def load_pair(ado_path: Path, dat_path: Path) -> Material:
    ado_entries = [parse_ado_entry(b) for b in split_ado_entries(ado_path.read_text())]
    dat_entries_raw = [parse_dat_entry(b) for b in split_dat_entries(dat_path.read_text())]
    dat_by_index = {d["entry_index"]: d for d in dat_entries_raw if d.get("entry_index")}

    merged: list[NetEntry] = []
    for a in ado_entries:
        d = dat_by_index.get(a.entry_index, {})
        # Sanity: if both sources have a title_formula, they should agree.
        if d.get("title_formula") and a.title_formula and d["title_formula"] != a.title_formula:
            a.parse_error = (a.parse_error or "") + f" | title mismatch: ado={a.title_formula} dat={d['title_formula']}"
        # Merge .dat fields into the ado-derived entry.
        for k in ("refcode", "cif_filename", "space_group", "crystal_class",
                  "pearson_symbol", "z_value", "cell_a", "cell_b", "cell_c",
                  "cell_alpha", "cell_beta", "cell_gamma", "cell_volume", "centat"):
            if d.get(k) is not None:
                setattr(a, k, d[k])
        a.simplig = d.get("simplig", {})
        a.composition = parse_formula(a.title_formula)
        merged.append(a)

    return Material(
        database=infer_database(ado_path),
        source_basename=ado_path.stem,
        entries=merged,
    )

def load_dataset(root: Path, pattern: str = "*SingleNodeSimpl*") -> list[Material]:
    """
    Pairs .ado and .dat files by stem. Skips files without a matching pair.
    Use pattern='*noMeMe_no01_SingleNodeSimpl_no012*' for the PDF's recommended starting set.
    """
    ados = {p.stem: p for p in root.glob(f"{pattern}.ado")}
    dats = {p.stem: p for p in root.glob(f"{pattern}.dat")}
    materials = []
    for stem in sorted(set(ados) & set(dats)):
        materials.append(load_pair(ados[stem], dats[stem]))
    missing = set(ados) ^ set(dats)
    if missing:
        print(f"Warning: {len(missing)} files without a pair: {sorted(missing)[:5]}...")
    return materials

# Quick sanity check for your dev loop:
if __name__ == "__main__":
    import json, sys
    from dataclasses import asdict
    root = Path(sys.argv[1])
    materials = load_dataset(root)
    print(f"Loaded {len(materials)} materials, {sum(len(m.entries) for m in materials)} entries total")
    # One representative, as JSON:
    m = materials[0]
    print(json.dumps(asdict(m), indent=2, default=str)[:2000])