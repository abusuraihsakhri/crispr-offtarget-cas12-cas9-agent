import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from crispr_offtarget_scan.models import FrontierPayload, ExecutionStatus
from crispr_offtarget_scan.engine import FrontierDomainEngine
from crispr_offtarget_scan.agents import CFDPenaltyMatrixAgent, PAMDistalMismatchAgent, GenomeLocusLocatorAgent, CRISPRScanCoordinator
from crispr_offtarget_scan.cli import main


def test_sub_agents():
    a1 = CFDPenaltyMatrixAgent()
    p1 = FrontierPayload("T1", "KEY-01", primary_metric=35.0, secondary_metric=4.0, status_descriptor="NOMINAL")
    alerts1 = a1.audit(p1)
    assert len(alerts1) == 1
    assert alerts1[0].status == ExecutionStatus.ELEVATED_RISK

    a2 = PAMDistalMismatchAgent()
    p2 = FrontierPayload("T2", "KEY-02", primary_metric=10.0, secondary_metric=15.0, status_descriptor="NOMINAL", is_critical_flag=True)
    alerts2 = a2.audit(p2)
    assert len(alerts2) == 1
    assert alerts2[0].status == ExecutionStatus.CRITICAL_INTERVENTION

    a3 = GenomeLocusLocatorAgent()
    p3 = FrontierPayload("T3", "KEY-03", primary_metric=10.0, secondary_metric=4.0, status_descriptor="DISCORDANT_ANOMALY")
    alerts3 = a3.audit(p3)
    assert len(alerts3) == 1


def test_coordinator():
    coord = CRISPRScanCoordinator()
    p_nominal = FrontierPayload("T4", "KEY-04", primary_metric=12.0, secondary_metric=4.0, status_descriptor="NOMINAL")
    dossier = coord.process(p_nominal)
    assert dossier["overall_status"] == ExecutionStatus.NOMINAL.value
    assert dossier["total_alerts"] == 0

    ans = coord.query_supervisory_chat("What standard is applied?")
    assert "Doench 2016 / Hsu 2013 CRISPR Algorithms" in ans or "specifications" in ans


def test_cli():
    assert main(["audit", "--task-id", "CLI-01"]) == 0
    assert main(["chat", "What", "is", "the", "system", "status?"]) == 0
