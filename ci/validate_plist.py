#!/usr/bin/env python3
"""Check Apple Shortcuts plist structure; not a substitute for iPhone testing."""
from pathlib import Path
import plistlib
import re
import sys

def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: validate_plist.py path/to/file.xml")
    path=Path(sys.argv[1])
    if not path.is_file() or path.stat().st_size < 100:
        raise SystemExit(f"Shortcut missing or too small: {path}")
    try:
        doc=plistlib.loads(path.read_bytes())
    except Exception as exc:
        raise SystemExit(f"Invalid plist: {exc}")
    if not isinstance(doc,dict):
        raise SystemExit("Expected a dictionary at plist root")
    acts=doc.get("WFWorkflowActions")
    if not isinstance(acts,list) or not acts:
        raise SystemExit("WFWorkflowActions is empty")
    errors=[]
    for i,action in enumerate(acts,1):
        if not isinstance(action,dict):
            errors.append(f"{i}: action is not a dictionary")
            continue
        aid=action.get("WFWorkflowActionIdentifier")
        if not isinstance(aid,str) or not aid.strip() or "unknown" in aid.lower():
            errors.append(f"{i}: absent or unknown action identifier")
        if not isinstance(action.get("WFWorkflowActionParameters"),dict):
            errors.append(f"{i}: missing action parameters dictionary")
    text=path.read_text(encoding="utf-8",errors="ignore")
    if re.search(r"sk-(?:proj-)?[A-Za-z0-9_-]{25,}",text):
        errors.append("Potential hardcoded API key")
    if errors:
        raise SystemExit("Static check failed:\n" + "\n".join(errors))
    print(f"Plist structural check passed: {len(acts)} actions.")
    print("NOTE: this does NOT establish six-feature coverage, proper wiring or importability.")

if __name__ == "__main__":
    main()
