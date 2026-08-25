#!/usr/bin/env python3
"""
Comprehensive Unit Test Suite for CRISPR Cas12a vs Cas9 Off-Target Engine
Tests SpCas9 and AsCas12a position weight models, seed mismatch sensitivity,
cleavage probability calculations, specificity score aggregation, and CLI commands.
"""

import unittest
from crispr_cas12_cas9 import (
    CRISPRCas12Cas9Engine,
    NucleaseComparisonResult,
    OffTargetAssessment,
    MismatchDetail,
    main,
)


class TestSpCas9CleavageModel(unittest.TestCase):
    """Test suite for SpCas9 Hsu-Zhang cleavage probability modeling."""

    def test_perfect_match_100_percent(self):
        seq = "GACACCGTGGACAGCAACAT"
        prob, mms = CRISPRCas12Cas9Engine.calculate_spcas9_cleavage_prob(seq, seq)
        self.assertEqual(prob, 100.0)
        self.assertEqual(len(mms), 0)

    def test_single_pam_distal_mismatch_tolerated(self):
        # Mismatch at position 1 (PAM-distal) is well-tolerated (~60-90% cleavage)
        on =  "GACACCGTGGACAGCAACAT"
        off = "TACACCGTGGACAGCAACAT"  # pos 1 G->T
        prob, mms = CRISPRCas12Cas9Engine.calculate_spcas9_cleavage_prob(on, off)
        self.assertEqual(len(mms), 1)
        self.assertFalse(mms[0].is_seed_region)
        self.assertGreater(prob, 80.0)

    def test_single_seed_mismatch_severely_penalized(self):
        # Mismatch at position 19 or 20 (adjacent to PAM) severely cuts cleavage
        on =  "GACACCGTGGACAGCAACAT"
        off = "GACACCGTGGACAGCAACAA"  # pos 20 T->A
        prob, mms = CRISPRCas12Cas9Engine.calculate_spcas9_cleavage_prob(on, off)
        self.assertEqual(len(mms), 1)
        self.assertTrue(mms[0].is_seed_region)
        self.assertLess(prob, 10.0)

    def test_multiple_mismatches_drop_prob_to_zero(self):
        on =  "GACACCGTGGACAGCAACAT"
        off = "GACACCGTCCACAGCAAGAT"  # multiple mismatches
        prob, mms = CRISPRCas12Cas9Engine.calculate_spcas9_cleavage_prob(on, off)
        self.assertGreaterEqual(len(mms), 2)
        self.assertLess(prob, 5.0)


class TestCas12aCleavageModel(unittest.TestCase):
    """Test suite for AsCas12a/LbCas12a 5' seed cleavage modeling."""

    def test_cas12a_perfect_match(self):
        seq = "ATGCGATCGATCGATCGATCGAT"
        prob, mms = CRISPRCas12Cas9Engine.calculate_cas12a_cleavage_prob(seq, seq)
        self.assertEqual(prob, 100.0)
        self.assertEqual(len(mms), 0)

    def test_cas12a_5prime_seed_mismatch_abolishes_cut(self):
        # Mismatch at position 2 (within 5' seed pos 1-8) severely abolishes cutting
        on =  "ATGCGATCGATCGATCGATCGAT"
        off = "ACGCGATCGATCGATCGATCGAT"  # pos 2 T->C
        prob, mms = CRISPRCas12Cas9Engine.calculate_cas12a_cleavage_prob(on, off)
        self.assertEqual(len(mms), 1)
        self.assertTrue(mms[0].is_seed_region)
        self.assertLess(prob, 10.0)

    def test_cas12a_3prime_distal_mismatch_tolerated(self):
        # Mismatch at position 22 (distal) is more tolerated
        on =  "ATGCGATCGATCGATCGATCGAT"
        off = "ATGCGATCGATCGATCGATCGAA"  # pos 23 T->A
        prob, mms = CRISPRCas12Cas9Engine.calculate_cas12a_cleavage_prob(on, off)
        self.assertEqual(len(mms), 1)
        self.assertFalse(mms[0].is_seed_region)
        self.assertGreater(prob, 70.0)


class TestNucleaseComparisonAndSpecificity(unittest.TestCase):
    """Test suite for guide specificity tiering and architecture differences."""

    def test_spcas9_guide_evaluation(self):
        on = "GACACCGTGGACAGCAACAT"
        off_candidates = [
            {"name": "OT-01", "sequence": "TACACCGTGGACAGCAACAT"},  # pos 1 (high cleavage)
            {"name": "OT-02", "sequence": "GACACCGTGGACAGCAACAA"},  # pos 20 (low cleavage)
        ]
        res = CRISPRCas12Cas9Engine.evaluate_guide(
            guide_id="G-TEST-01",
            on_target_sequence=on,
            nuclease_type="SpCas9",
            off_target_candidates=off_candidates,
        )
        self.assertEqual(res.nuclease_type, "SpCas9")
        self.assertEqual(res.pam_orientation, "3_PRIME_NGG")
        self.assertEqual(res.cut_type, "Blunt double-strand break (3 nt upstream of PAM)")
        self.assertEqual(len(res.evaluated_off_target_sites), 2)
        self.assertGreater(res.overall_specificity_score, 0.0)

    def test_cas12a_guide_evaluation(self):
        on = "ATGCGATCGATCGATCGATCGAT"
        res = CRISPRCas12Cas9Engine.evaluate_guide(
            guide_id="G-TEST-02",
            on_target_sequence=on,
            nuclease_type="AsCas12a",
        )
        self.assertEqual(res.nuclease_type, "AsCas12a")
        self.assertEqual(res.pam_orientation, "5_PRIME_TTTV")
        self.assertEqual(res.fidelity_tier, "ULTRA_HIGH_SPECIFICITY")


class TestEndToEndAndCLI(unittest.TestCase):
    """Test suite for JSON export and CLI commands."""

    def test_json_export(self):
        res = CRISPRCas12Cas9Engine.evaluate_guide("G-01", "GACACCGTGGACAGCAACAT", "SpCas9")
        json_str = res.to_json()
        self.assertIn("SpCas9", json_str)
        self.assertIn("overall_specificity_score", json_str)

    def test_cli_eval_command(self):
        self.assertEqual(main(["eval", "--seq", "GACACCGTGGACAGCAACAT", "--nuclease", "SpCas9"]), 0)
        self.assertEqual(main(["eval", "--seq", "ATGCGATCGATCGATCGATCGAT", "--nuclease", "AsCas12a", "--json"]), 0)

    def test_cli_chat_command(self):
        self.assertEqual(main(["chat", "What", "is", "the", "difference", "between", "Cas9", "and", "Cas12a?"]), 0)


if __name__ == "__main__":
    unittest.main()
