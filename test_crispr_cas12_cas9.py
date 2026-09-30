#!/usr/bin/env python3
"""Unit tests for the research-use Cas9/Cas12a mismatch heuristic."""

import unittest

from crispr_cas12_cas9 import CRISPRCas12Cas9Engine, main


class TestSpCas9CleavageModel(unittest.TestCase):
    def test_perfect_match_100_percent(self):
        sequence = "GACACCGTGGACAGCAACAT"
        probability, mismatches = CRISPRCas12Cas9Engine.calculate_spcas9_cleavage_prob(
            sequence, sequence
        )
        self.assertEqual(probability, 100.0)
        self.assertEqual(mismatches, [])

    def test_single_pam_distal_mismatch_tolerated(self):
        on_target = "GACACCGTGGACAGCAACAT"
        off_target = "TACACCGTGGACAGCAACAT"
        probability, mismatches = CRISPRCas12Cas9Engine.calculate_spcas9_cleavage_prob(
            on_target, off_target
        )
        self.assertEqual(len(mismatches), 1)
        self.assertFalse(mismatches[0].is_seed_region)
        self.assertGreater(probability, 80.0)

    def test_single_seed_mismatch_severely_penalized(self):
        on_target = "GACACCGTGGACAGCAACAT"
        off_target = "GACACCGTGGACAGCAACAA"
        probability, mismatches = CRISPRCas12Cas9Engine.calculate_spcas9_cleavage_prob(
            on_target, off_target
        )
        self.assertEqual(len(mismatches), 1)
        self.assertTrue(mismatches[0].is_seed_region)
        self.assertLess(probability, 10.0)

    def test_multiple_mismatches_drop_probability(self):
        on_target = "GACACCGTGGACAGCAACAT"
        off_target = "GACACCGTCCACAGCAAGAT"
        probability, mismatches = CRISPRCas12Cas9Engine.calculate_spcas9_cleavage_prob(
            on_target, off_target
        )
        self.assertGreaterEqual(len(mismatches), 2)
        self.assertLess(probability, 5.0)

    def test_requires_exact_length(self):
        with self.assertRaisesRegex(ValueError, "exactly 20 nt"):
            CRISPRCas12Cas9Engine.calculate_spcas9_cleavage_prob("ACGT", "ACGT")


class TestCas12aCleavageModel(unittest.TestCase):
    def test_cas12a_perfect_match(self):
        sequence = "ATGCGATCGATCGATCGATCGAT"
        probability, mismatches = CRISPRCas12Cas9Engine.calculate_cas12a_cleavage_prob(
            sequence, sequence
        )
        self.assertEqual(probability, 100.0)
        self.assertEqual(mismatches, [])

    def test_cas12a_5prime_seed_mismatch_abolishes_cut(self):
        on_target = "ATGCGATCGATCGATCGATCGAT"
        off_target = "ACGCGATCGATCGATCGATCGAT"
        probability, mismatches = CRISPRCas12Cas9Engine.calculate_cas12a_cleavage_prob(
            on_target, off_target
        )
        self.assertEqual(len(mismatches), 1)
        self.assertTrue(mismatches[0].is_seed_region)
        self.assertLess(probability, 10.0)

    def test_cas12a_3prime_distal_mismatch_tolerated(self):
        on_target = "ATGCGATCGATCGATCGATCGAT"
        off_target = "ATGCGATCGATCGATCGATCGAA"
        probability, mismatches = CRISPRCas12Cas9Engine.calculate_cas12a_cleavage_prob(
            on_target, off_target
        )
        self.assertEqual(len(mismatches), 1)
        self.assertFalse(mismatches[0].is_seed_region)
        self.assertGreater(probability, 70.0)

    def test_requires_exact_length(self):
        with self.assertRaisesRegex(ValueError, "exactly 23 nt"):
            CRISPRCas12Cas9Engine.calculate_cas12a_cleavage_prob("ACGT", "ACGT")


class TestNucleaseComparisonAndSpecificity(unittest.TestCase):
    def test_spcas9_guide_evaluation(self):
        on_target = "GACACCGTGGACAGCAACAT"
        candidates = [
            {"name": "OT-01", "sequence": "TACACCGTGGACAGCAACAT"},
            {"name": "OT-02", "sequence": "GACACCGTGGACAGCAACAA"},
        ]
        result = CRISPRCas12Cas9Engine.evaluate_guide(
            guide_id="G-TEST-01",
            on_target_sequence=on_target,
            nuclease_type="SpCas9",
            off_target_candidates=candidates,
        )
        self.assertEqual(result.nuclease_type, "SpCas9")
        self.assertEqual(result.pam_orientation, "3_PRIME_NGG")
        self.assertIn("Blunt double-strand break", result.cut_type)
        self.assertEqual(len(result.evaluated_off_target_sites), 2)
        self.assertGreater(result.overall_specificity_score, 0.0)

    def test_no_candidates_is_not_assessed(self):
        result = CRISPRCas12Cas9Engine.evaluate_guide(
            guide_id="G-TEST-02",
            on_target_sequence="ATGCGATCGATCGATCGATCGAT",
            nuclease_type="AsCas12a",
        )
        self.assertEqual(result.fidelity_tier, "NOT_ASSESSED")
        self.assertEqual(result.overall_specificity_score, 0.0)

    def test_exact_match_candidate_counts_as_high_risk(self):
        sequence = "GACACCGTGGACAGCAACAT"
        result = CRISPRCas12Cas9Engine.evaluate_guide(
            on_target_sequence=sequence,
            nuclease_type="SpCas9",
            off_target_candidates=[{"name": "duplicate-locus", "sequence": sequence}],
        )
        assessment = result.evaluated_off_target_sites[0]
        self.assertEqual(assessment.mismatch_count, 0)
        self.assertEqual(assessment.cleavage_probability_percent, 100.0)
        self.assertEqual(assessment.risk_level, "HIGH_RISK_CLEAVAGE")
        self.assertLess(result.overall_specificity_score, 10.0)

    def test_invalid_nuclease_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported nuclease"):
            CRISPRCas12Cas9Engine.evaluate_guide(
                on_target_sequence="GACACCGTGGACAGCAACAT",
                nuclease_type="Cas13",
            )

    def test_candidate_requires_sequence(self):
        with self.assertRaisesRegex(ValueError, "missing a sequence"):
            CRISPRCas12Cas9Engine.evaluate_guide(
                on_target_sequence="GACACCGTGGACAGCAACAT",
                nuclease_type="SpCas9",
                off_target_candidates=[{"name": "OT-01"}],
            )


class TestEndToEndAndCLI(unittest.TestCase):
    def test_json_export(self):
        result = CRISPRCas12Cas9Engine.evaluate_guide(
            "G-01",
            "GACACCGTGGACAGCAACAT",
            "SpCas9",
            [{"name": "OT-01", "sequence": "TACACCGTGGACAGCAACAT"}],
        )
        json_text = result.to_json()
        self.assertIn("SpCas9", json_text)
        self.assertIn("overall_specificity_score", json_text)

    def test_cli_eval_command(self):
        self.assertEqual(
            main(
                [
                    "eval",
                    "--seq",
                    "GACACCGTGGACAGCAACAT",
                    "--nuclease",
                    "SpCas9",
                    "--offtargets",
                    "TACACCGTGGACAGCAACAT",
                ]
            ),
            0,
        )
        self.assertEqual(
            main(
                [
                    "eval",
                    "--seq",
                    "ATGCGATCGATCGATCGATCGAT",
                    "--nuclease",
                    "AsCas12a",
                    "--offtargets",
                    "ATGCGATCGATCGATCGATCGAA",
                    "--json",
                ]
            ),
            0,
        )

    def test_cli_chat_command(self):
        self.assertEqual(main(["chat", "What", "does", "the", "model", "do?"]), 0)


if __name__ == "__main__":
    unittest.main()
