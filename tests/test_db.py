"""
tests/test_db.py — Unit tests for database boundary helpers.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.db import normalize_reaction_target_guid


def test_normalize_reaction_target_guid():
    uuid = "008F6B46-281F-4B0A-B059-A9EDA7870A82"
    assert normalize_reaction_target_guid(f"bp:{uuid}") == uuid
    assert normalize_reaction_target_guid(f"p:0/{uuid}") == uuid
    assert normalize_reaction_target_guid(f"p:1/{uuid}") == uuid
    assert normalize_reaction_target_guid("guid-1") == "guid-1"
    assert normalize_reaction_target_guid(None) == ""
    assert normalize_reaction_target_guid("   ") == ""
