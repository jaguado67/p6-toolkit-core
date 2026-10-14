"""Module contract: every tool is one file in ui/modules exposing SPEC and render(ctx)."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleSpec:
    id: str            # catalogue number (M01..M14)
    name: str          # navigation label
    maturity: str      # honest implementation status shown in the scope table
    needs_xer: bool = True   # False: the shell does not require loaded XER snapshots
