# models.py
from dataclasses import dataclass, field, asdict
from typing import Optional
from collections import Counter

@dataclass
class Sublattice:
    """One ZA1/ZB3/etc. entry within a net."""
    name: str                              # e.g. "ZA1"
    coordination_sequence: list[int]       # Cum row, 10 entries (may be shorter if truncated)
    coordination_numerators: list[int]     # Num row
    point_symbol: Optional[str] = None     # e.g. "{4^12.6^3}"
    extended_point_symbol: Optional[str] = None

@dataclass
class NetEntry:
    """One numbered entry within an .ado file (and its matching .dat entry)."""
    entry_index: int                       # the leading integer, e.g. 3
    header: str                            # full header line after the integer
    title_formula: str                     # e.g. "ZnH17C12Br(NO)2"
    rings_threshold: Optional[int] = None  # the ">6" or ">8" part

    # --- from .ado ---
    sublattices: list[Sublattice] = field(default_factory=list)
    td10: Optional[int] = None
    net_point_symbol: Optional[str] = None
    topological_type: Optional[str] = None # e.g. "pcu" or "unj"
    interpenetration: Optional[str] = None # e.g. "Totally 2(1+1) interpenetrating nets"
    is_framework: bool = False             # "3D framework with ZA" line present
    parse_error: Optional[str] = None      # non-None if the .ado entry looks degenerate

    # --- from .dat ---
    refcode: Optional[str] = None          # e.g. "ABUWOJ" (from Comment: File: ABUWOJ_...)
    cif_filename: Optional[str] = None
    space_group: Optional[str] = None
    crystal_class: Optional[str] = None
    pearson_symbol: Optional[str] = None
    z_value: Optional[int] = None
    cell_a: Optional[float] = None
    cell_b: Optional[float] = None
    cell_c: Optional[float] = None
    cell_alpha: Optional[float] = None
    cell_beta: Optional[float] = None
    cell_gamma: Optional[float] = None
    cell_volume: Optional[float] = None
    centat: Optional[str] = None           # "none" or a composition string
    simplig: dict[str, str] = field(default_factory=dict)  # {"ZA": "C4O10Zn4", "ZB": "C6", ...}
    composition: dict[str, int] = field(default_factory=dict)  # parsed from title, e.g. {"Zn":1,"H":17,...}

@dataclass
class Material:
    """All entries that share a source file pair (one material, possibly multiple ring thresholds)."""
    database: str                          # "CCDC", "CSD", or "CoreMOF" — from filename
    source_basename: str                   # the ado/dat filename stem
    entries: list[NetEntry] = field(default_factory=list)

    def primary_entry(self) -> Optional[NetEntry]:
        """PDF says: 'take the one with the smallest number' for a start."""
        valid = [e for e in self.entries if e.parse_error is None]
        return min(valid, key=lambda e: e.entry_index) if valid else None