#!/usr/bin/env python3
"""
Research-use Cas9/Cas12a off-target mismatch heuristic.

This module uses simplified position-dependent mismatch penalties inspired by
published CRISPR specificity work. It is not an implementation of the complete
Doench CFD matrix, does not perform genome-wide locus discovery, and is not a
clinical decision-support system.
"""

import argparse
import csv
import json
import os
import sys
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple


SPCAS9_POSITION_WEIGHTS = {
    1: 0.014, 2: 0.000, 3: 0.039, 4: 0.040, 5: 0.060,
    6: 0.070, 7: 0.080, 8: 0.100, 9: 0.120, 10: 0.150,
    11: 0.200, 12: 0.250, 13: 0.350, 14: 0.450, 15: 0.600,
    16: 0.700, 17: 0.800, 18: 0.850, 19: 0.900, 20: 0.950,
}

CAS12A_POSITION_WEIGHTS = {
    1: 0.950, 2: 0.950, 3: 0.920, 4: 0.900, 5: 0.880,
    6: 0.850, 7: 0.800, 8: 0.750, 9: 0.600, 10: 0.500,
    11: 0.400, 12: 0.350, 13: 0.300, 14: 0.250, 15: 0.200,
    16: 0.150, 17: 0.120, 18: 0.100, 19: 0.080, 20: 0.060,
    21: 0.040, 22: 0.020, 23: 0.010,
}


@dataclass
class MismatchDetail:
    position_1_indexed: int
    guide_base: str
    target_base: str
    is_seed_region: bool
    position_penalty_factor: float
    mismatch_type: str


@dataclass
class OffTargetAssessment:
    site_name: str
    off_target_sequence: str
    mismatch_count: int
    seed_mismatches_count: int
    cleavage_probability_percent: float
    risk_level: str
    mismatch_details: List[MismatchDetail]


@dataclass
class NucleaseComparisonResult:
    guide_id: str
    on_target_sequence: str
    nuclease_type: str
    pam_motif: str
    pam_orientation: str
    seed_region_definition: str
    cut_type: str
    overall_specificity_score: float
    fidelity_tier: str
    evaluated_off_target_sites: List[OffTargetAssessment]
    # Kept for backward compatibility. Text is research-use interpretation only.
    clinical_recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class CRISPRCas12Cas9Engine:
    """Simplified position-weighted mismatch model for supplied candidate sequences."""

    @staticmethod
    def _validate_sequence(seq: str, context: str, expected_length: int) -> str:
        if seq is None or str(seq).strip() == "":
            raise ValueError(f"{context} sequence cannot be empty")
        sanitized = str(seq).upper().strip()
        invalid = set(sanitized) - set("ACGT")
        if invalid:
            invalid_display = "".join(sorted(invalid))
            raise ValueError(
                f"{context} sequence contains invalid characters: {invalid_display}. "
                "Only A, C, G, T are allowed."
            )
        if len(sanitized) != expected_length:
            raise ValueError(
                f"{context} sequence must be exactly {expected_length} nt; "
                f"received {len(sanitized)} nt"
            )
        return sanitized

    @staticmethod
    def _normalize_nuclease(nuclease_type: str) -> str:
        normalized = str(nuclease_type).strip().lower().replace("-", "")
        if normalized in {"spcas9", "cas9"}:
            return "SpCas9"
        if normalized in {"ascas12a", "lbcas12a", "cas12a", "cpf1"}:
            return "AsCas12a"
        raise ValueError(
            f"Unsupported nuclease {nuclease_type!r}. Use SpCas9 or AsCas12a."
        )

    @staticmethod
    def calculate_spcas9_cleavage_prob(
        on_target: str,
        off_target: str,
    ) -> Tuple[float, List[MismatchDetail]]:
        """Return a heuristic cleavage score for two 20-nt SpCas9 protospacers."""
        on_target = CRISPRCas12Cas9Engine._validate_sequence(on_target, "On-target", 20)
        off_target = CRISPRCas12Cas9Engine._validate_sequence(off_target, "Off-target", 20)

        mismatches: List[MismatchDetail] = []
        mismatch_positions: List[int] = []
        weight_product = 1.0

        for index, (guide_base, target_base) in enumerate(zip(on_target, off_target), start=1):
            if guide_base == target_base:
                continue
            weight = SPCAS9_POSITION_WEIGHTS[index]
            weight_product *= 1.0 - weight
            mismatch_positions.append(index)
            mismatches.append(
                MismatchDetail(
                    position_1_indexed=index,
                    guide_base=guide_base,
                    target_base=target_base,
                    is_seed_region=index >= 11,
                    position_penalty_factor=round(weight, 3),
                    mismatch_type=f"r{guide_base}:d{target_base}",
                )
            )

        mismatch_count = len(mismatches)
        if mismatch_count == 0:
            return 100.0, []

        if mismatch_count > 1:
            mean_distance = (
                mismatch_positions[-1] - mismatch_positions[0]
            ) / (mismatch_count - 1)
        else:
            mean_distance = 19.0

        distance_factor = 1.0 / (((19.0 - mean_distance) / 19.0) * 4.0 + 1.0)
        count_factor = 1.0 / (mismatch_count**2)
        probability = weight_product * distance_factor * count_factor * 100.0
        return max(0.001, min(100.0, probability)), mismatches

    @staticmethod
    def calculate_cas12a_cleavage_prob(
        on_target: str,
        off_target: str,
    ) -> Tuple[float, List[MismatchDetail]]:
        """Return a heuristic cleavage score for two 23-nt Cas12a protospacers."""
        on_target = CRISPRCas12Cas9Engine._validate_sequence(on_target, "On-target", 23)
        off_target = CRISPRCas12Cas9Engine._validate_sequence(off_target, "Off-target", 23)

        mismatches: List[MismatchDetail] = []
        weight_product = 1.0

        for index, (guide_base, target_base) in enumerate(zip(on_target, off_target), start=1):
            if guide_base == target_base:
                continue
            weight = CAS12A_POSITION_WEIGHTS[index]
            weight_product *= 1.0 - weight
            mismatches.append(
                MismatchDetail(
                    position_1_indexed=index,
                    guide_base=guide_base,
                    target_base=target_base,
                    is_seed_region=index <= 8,
                    position_penalty_factor=round(weight, 3),
                    mismatch_type=f"r{guide_base}:d{target_base}",
                )
            )

        mismatch_count = len(mismatches)
        if mismatch_count == 0:
            return 100.0, []

        count_factor = 1.0 / (mismatch_count**2.2)
        probability = weight_product * count_factor * 100.0
        return max(0.0001, min(100.0, probability)), mismatches

    @classmethod
    def evaluate_guide(
        cls,
        guide_id: str = "GUIDE-001",
        on_target_sequence: str = "GACACCGTGGACAGCAACAT",
        nuclease_type: str = "SpCas9",
        off_target_candidates: Optional[List[Dict[str, str]]] = None,
    ) -> NucleaseComparisonResult:
        """Evaluate supplied candidate sequences; this function does not search a genome."""
        nuclease = cls._normalize_nuclease(nuclease_type)
        expected_length = 20 if nuclease == "SpCas9" else 23
        on_target_sequence = cls._validate_sequence(
            on_target_sequence,
            "On-target",
            expected_length,
        )
        candidates = [] if off_target_candidates is None else off_target_candidates

        assessments: List[OffTargetAssessment] = []
        total_candidate_cleavage = 0.0

        for index, candidate in enumerate(candidates, start=1):
            if not isinstance(candidate, dict):
                raise ValueError(f"Off-target candidate {index} must be an object/dictionary")
            if "sequence" not in candidate:
                raise ValueError(f"Off-target candidate {index} is missing a sequence")

            site_name = str(candidate.get("name") or f"OT-{index:02d}")
            sequence = candidate["sequence"]

            if nuclease == "SpCas9":
                probability, mismatch_list = cls.calculate_spcas9_cleavage_prob(
                    on_target_sequence,
                    sequence,
                )
            else:
                probability, mismatch_list = cls.calculate_cas12a_cleavage_prob(
                    on_target_sequence,
                    sequence,
                )

            seed_mismatches = sum(item.is_seed_region for item in mismatch_list)
            mismatch_count = len(mismatch_list)
            if probability >= 20.0:
                risk_level = "HIGH_RISK_CLEAVAGE"
            elif probability >= 5.0:
                risk_level = "MODERATE"
            elif probability >= 0.5:
                risk_level = "LOW"
            else:
                risk_level = "NEGLIGIBLE"

            total_candidate_cleavage += probability
            assessments.append(
                OffTargetAssessment(
                    site_name=site_name,
                    off_target_sequence=str(sequence).upper().strip(),
                    mismatch_count=mismatch_count,
                    seed_mismatches_count=seed_mismatches,
                    cleavage_probability_percent=round(probability, 3),
                    risk_level=risk_level,
                    mismatch_details=mismatch_list,
                )
            )

        if assessments:
            specificity_score = round(
                max(0.0, min(100.0, 100.0 / (1.0 + total_candidate_cleavage / 10.0))),
                1,
            )
            if specificity_score >= 85.0:
                tier = "HIGH_HEURISTIC_SPECIFICITY"
                recommendation = (
                    "Low aggregate cleavage score across the supplied candidates. "
                    "Validate experimentally and with genome-aware off-target discovery."
                )
            elif specificity_score >= 65.0:
                tier = "INTERMEDIATE_HEURISTIC_SPECIFICITY"
                recommendation = (
                    "Intermediate aggregate candidate risk. Expand candidate discovery "
                    "and perform orthogonal experimental validation."
                )
            elif specificity_score >= 40.0:
                tier = "ELEVATED_HEURISTIC_RISK"
                recommendation = (
                    "Elevated aggregate candidate risk in this heuristic model. "
                    "Consider alternative guides and experimental validation."
                )
            else:
                tier = "HIGH_HEURISTIC_RISK"
                recommendation = (
                    "High aggregate candidate cleavage score in this heuristic model. "
                    "Do not treat this result as a clinical decision."
                )
        else:
            specificity_score = 0.0
            tier = "NOT_ASSESSED"
            recommendation = (
                "No off-target candidates were supplied, so specificity cannot be assessed. "
                "Provide candidate loci from a genome-aware search before interpreting risk."
            )

        if nuclease == "SpCas9":
            pam = "5'-NGG-3'"
            pam_orientation = "3_PRIME_NGG"
            seed_definition = "PAM-proximal positions 11-20 in this simplified model"
            cut_type = "Blunt double-strand break (approximately 3 nt upstream of PAM)"
        else:
            pam = "5'-TTTV-3'"
            pam_orientation = "5_PRIME_TTTV"
            seed_definition = "PAM-proximal positions 1-8 in this simplified model"
            cut_type = "Staggered double-strand break"

        return NucleaseComparisonResult(
            guide_id=str(guide_id),
            on_target_sequence=on_target_sequence,
            nuclease_type=nuclease,
            pam_motif=pam,
            pam_orientation=pam_orientation,
            seed_region_definition=seed_definition,
            cut_type=cut_type,
            overall_specificity_score=specificity_score,
            fidelity_tier=tier,
            evaluated_off_target_sites=assessments,
            clinical_recommendation=recommendation,
        )


def _validate_safe_path(filepath: str) -> str:
    raw_path = os.fspath(filepath)
    if any(part == ".." for part in raw_path.replace("\\", "/").split("/")):
        raise argparse.ArgumentTypeError(
            f"Path traversal detected in '{filepath}'. Paths must not contain '..' segments."
        )
    return os.path.normpath(raw_path)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="crispr-offtarget",
        description="Research-use Cas9/Cas12a supplied-candidate mismatch heuristic",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_eval = subparsers.add_parser("eval", help="Evaluate a guide against supplied candidate sequences")
    p_eval.add_argument("--guide-id", default="GUIDE-2026-001")
    p_eval.add_argument("--seq", "-s", required=True)
    p_eval.add_argument("--nuclease", "-n", default="SpCas9", choices=["SpCas9", "AsCas12a"])
    p_eval.add_argument("--offtargets", nargs="*", default=[])
    p_eval.add_argument("--json", action="store_true")

    p_chat = subparsers.add_parser("chat", help="Show model-scope information")
    p_chat.add_argument("query", nargs="+")

    p_batch = subparsers.add_parser("batch", help="Batch process guide records from CSV")
    p_batch.add_argument("-i", "--input", required=True, type=_validate_safe_path)
    p_batch.add_argument("-o", "--output", default="cas_comparison_results.csv", type=_validate_safe_path)

    args = parser.parse_args(argv)

    if args.command == "eval":
        candidates = [
            {"name": f"OT-{index + 1:02d}", "sequence": sequence}
            for index, sequence in enumerate(args.offtargets)
        ]
        result = CRISPRCas12Cas9Engine.evaluate_guide(
            guide_id=args.guide_id,
            on_target_sequence=args.seq,
            nuclease_type=args.nuclease,
            off_target_candidates=candidates,
        )
        if args.json:
            print(result.to_json())
        else:
            print("=" * 80)
            print(f"  CRISPR {result.nuclease_type.upper()} SUPPLIED-CANDIDATE ASSESSMENT")
            print(f"  Guide: {result.guide_id} | Tier: [{result.fidelity_tier}]")
            print(f"  Heuristic specificity score: {result.overall_specificity_score:.1f} / 100")
            print("=" * 80)
            for candidate in result.evaluated_off_target_sites:
                print(
                    f"  [{candidate.risk_level:20s}] {candidate.site_name}: "
                    f"{candidate.off_target_sequence} | mismatches={candidate.mismatch_count} "
                    f"| score={candidate.cleavage_probability_percent:.3f}%"
                )
            print(f"\n  Interpretation: {result.clinical_recommendation}")
            print("  Research use only; not a validated CFD implementation or clinical tool.")
            print("=" * 80)
        return 0

    if args.command == "chat":
        query = " ".join(args.query).lower()
        if "cas12" in query or "cpf1" in query:
            print("Cas12a uses a 5' TTTV PAM and differs from SpCas9 in PAM orientation and cleavage pattern.")
        elif "seed" in query:
            print("This heuristic treats SpCas9 positions 11-20 and Cas12a positions 1-8 as PAM-proximal seed regions.")
        else:
            print(
                "This tool applies simplified position-weighted mismatch penalties to supplied "
                "candidate sequences. It is not the complete CFD model and does not search a genome."
            )
        return 0

    if args.command == "batch":
        with open(args.input, mode="r", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)

        out_rows = []
        for row in rows:
            guide_id = row.get("guide_id", "G-001")
            sequence = row.get("sequence", row.get("on_target", "GACACCGTGGACAGCAACAT"))
            nuclease = row.get("nuclease", "SpCas9")
            result = CRISPRCas12Cas9Engine.evaluate_guide(guide_id, sequence, nuclease)
            out_rows.append(
                {
                    **row,
                    "nuclease": result.nuclease_type,
                    "specificity_score": result.overall_specificity_score,
                    "fidelity_tier": result.fidelity_tier,
                    "cut_type": result.cut_type,
                }
            )

        if out_rows:
            with open(args.output, mode="w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(out_rows[0].keys()))
                writer.writeheader()
                writer.writerows(out_rows)
        print(f"Batch processed {len(out_rows)} rows -> {args.output}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
