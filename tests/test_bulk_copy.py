import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories import bulk_copy  # noqa: E402


def test_legacy_original_author_columns_are_always_imported_as_null():
    columns = ["authorid", "originalauthorid", "originalmergedby", "originalapprovedby",
               "originalfirstreviewedby", "originaldeclinedby", "title"]
    row = {"authorid": 10, "originalauthorid": 99, "originalmergedby": 98, "originalapprovedby": 97,
           "originalfirstreviewedby": 96, "originaldeclinedby": 95, "title": "x"}
    out = bulk_copy._row_to_copy_text(row, columns)
    assert out["authorid"] == "10" and out["title"] == "x"
    for col in bulk_copy.LEGACY_ORIGINAL_AUTHOR_COLUMNS:
        assert out[col] == "\\N"


def test_other_columns_keep_their_text_form():
    out = bulk_copy._row_to_copy_text({"a": None, "b": {"k": 1}, "c": [1]}, ["a", "b", "c", "missing"])
    assert out == {"a": "\\N", "b": '{"k":1}', "c": "[1]", "missing": ""}
