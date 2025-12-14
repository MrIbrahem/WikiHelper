# restore_refs_wtp.py
# Restore placeholders like [ref1] back to their original <ref ...>...</ref> tags
# using file_name.refs.json.

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict


PLACEHOLDER_PATTERN = re.compile(r"\[(ref\d+)\]")


def restore_refs_in_text(text: str, refs_map: Dict[str, str]) -> str:
    def _repl(match: re.Match) -> str:
        key = match.group(1)
        return refs_map.get(key, match.group(0))  # keep placeholder if missing
    return PLACEHOLDER_PATTERN.sub(_repl, text)
