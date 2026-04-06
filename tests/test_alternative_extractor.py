"""Tests for alternative_extractor.py — Story 9.2: merged alternatives split."""

import pytest

from src.enem_ingestion.alternative_extractor import (
    _split_merged_alternatives,
    create_enhanced_extractor,
)


# ---------------------------------------------------------------------------
# _split_merged_alternatives unit tests (Story 9.2)
# ---------------------------------------------------------------------------

class TestSplitMergedAlternatives:

    @pytest.mark.parametrize("input_dict,exp_d,exp_e", [
        # "D W. E T." → D="W.", E="T."
        ({"A": "x", "B": "y", "C": "z", "D": "W. E T."}, "W.", "T."),
        # "D 52. E 60."
        ({"A": "x", "B": "y", "C": "z", "D": "52. E 60."}, "52.", "60."),
        # "D 10[4] E 10[6]"
        ({"A": "x", "B": "y", "C": "z", "D": "10[4] E 10[6]"}, "10[4]", "10[6]"),
        # "D 18. E 20."
        ({"A": "x", "B": "y", "C": "z", "D": "18. E 20."}, "18.", "20."),
    ])
    def test_split_d_e(self, input_dict, exp_d, exp_e):
        result = _split_merged_alternatives(input_dict)
        assert result["D"] == exp_d
        assert result["E"] == exp_e

    def test_split_three_merged_c_d_e(self):
        """C contains D and E text: "C 1 e 2. D 1 e 3. E 2 e 3." """
        alts = {"A": "x", "B": "y", "C": "1 e 2. D 1 e 3. E 2 e 3."}
        result = _split_merged_alternatives(alts)
        assert result["E"] == "2 e 3."
        assert result["D"] == "1 e 3."
        assert result["C"] == "1 e 2."

    def test_no_split_when_e_exists(self):
        """Don't split D if E already exists."""
        alts = {"A": "x", "B": "y", "C": "z", "D": "something E else", "E": "original"}
        result = _split_merged_alternatives(alts)
        assert result["D"] == "something E else"
        assert result["E"] == "original"

    def test_no_false_positive_conjunction(self):
        """Don't split on 'E' that's a conjunction in long text."""
        alts = {"A": "x", "B": "y", "C": "z", "D": "Platão E aristóteles estudaram"}
        result = _split_merged_alternatives(alts)
        # Should NOT be split (long lowercase word after E)
        assert result["D"] == "Platão E aristóteles estudaram"
        assert "E" not in result

    def test_no_change_clean_alts(self):
        """Clean alternatives are not modified."""
        alts = {"A": "opt A", "B": "opt B", "C": "opt C", "D": "opt D", "E": "opt E"}
        result = _split_merged_alternatives(alts)
        assert result == alts

    def test_split_c_d(self):
        """Split C→D when D is missing."""
        alts = {"A": "x", "B": "y", "C": "5,00. D 5,83.", "E": "z"}
        result = _split_merged_alternatives(alts)
        assert result["C"] == "5,00."
        assert result["D"] == "5,83."
