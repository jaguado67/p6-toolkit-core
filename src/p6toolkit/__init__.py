"""P6 Toolkit Core: auditable project schedule data and diagnostics."""
from .xer import XERDocument, XERParseError, parse_xer_bytes, parse_xer_file
from .snapshot import ProjectSnapshot, build_snapshot, list_projects
from .compare import compare_snapshots
from .network import inspect_network
from .history import build_float_history

from .diagnostics import audit_logic, audit_constraints, summarize_snapshot, dcma_precheck, activity_status
from .converter import convert_workbook, convert_rows, to_import_workbook, ConverterError
from .progress import validate_progress

__all__ = ["XERDocument", "XERParseError", "parse_xer_bytes", "parse_xer_file",
           "ProjectSnapshot", "build_snapshot", "list_projects", "compare_snapshots",
           "inspect_network", "build_float_history",
           "audit_logic", "audit_constraints", "summarize_snapshot", "dcma_precheck", "activity_status",
           "convert_workbook", "convert_rows", "to_import_workbook", "ConverterError",
           "validate_progress"]
