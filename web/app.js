"use strict";

const PYODIDE_INDEX_URL = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";
let pyodideRuntime = null;
let lastResult = null;

const examples = {
  SpCas9: {
    onTarget: "GACACCGTGGACAGCAACAT",
    candidates: [
      "TACACCGTGGACAGCAACAT",
      "GACACCGTGGACAGCAACAA",
    ],
  },
  AsCas12a: {
    onTarget: "ATGCGATCGATCGATCGATCGAT",
    candidates: [
      "ACGCGATCGATCGATCGATCGAT",
      "ATGCGATCGATCGATCGATCGAA",
    ],
  },
};

function byId(id) {
  return document.getElementById(id);
}

function setRuntimeStatus(message, className = "") {
  const element = byId("runtime-status");
  element.textContent = message;
  element.className = "runtime-badge";
  if (className) {
    element.classList.add(className);
  }
}

function setMessage(message, className = "") {
  const element = byId("message");
  element.textContent = message;
  element.className = "message";
  if (className) {
    element.classList.add(className);
  }
}

function loadExample() {
  const nuclease = byId("nuclease").value;
  const example = examples[nuclease];
  byId("on-target").value = example.onTarget;
  byId("off-targets").value = example.candidates.join("\n");
}

function readCandidateSequences() {
  return byId("off-targets")
    .value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function expectedLength(nuclease) {
  return nuclease === "SpCas9" ? 20 : 23;
}

function validateSequence(sequence, label, length) {
  if (!/^[ACGT]+$/i.test(sequence)) {
    throw new Error(`${label} must contain only A, C, G, and T.`);
  }
  if (sequence.length !== length) {
    throw new Error(`${label} must be exactly ${length} nt; received ${sequence.length} nt.`);
  }
}

function validateInputs(nuclease, onTarget, candidates) {
  const length = expectedLength(nuclease);
  validateSequence(onTarget, "On-target sequence", length);
  candidates.forEach((sequence, index) => {
    validateSequence(sequence, `Candidate ${index + 1}`, length);
  });
}

function clearRows() {
  const body = byId("result-rows");
  while (body.firstChild) {
    body.removeChild(body.firstChild);
  }
}

function appendCell(row, text, className = "") {
  const cell = document.createElement("td");
  cell.textContent = String(text);
  if (className) {
    cell.className = className;
  }
  row.appendChild(cell);
}

function renderResult(result) {
  lastResult = result;
  byId("score-value").textContent = `${Number(result.overall_specificity_score).toFixed(1)} / 100`;
  byId("tier-value").textContent = result.fidelity_tier;
  byId("candidate-count").textContent = String(result.evaluated_off_target_sites.length);
  byId("interpretation-text").textContent = result.clinical_recommendation;

  clearRows();
  const body = byId("result-rows");
  result.evaluated_off_target_sites.forEach((candidate) => {
    const row = document.createElement("tr");
    appendCell(row, candidate.site_name);
    appendCell(row, candidate.off_target_sequence, "sequence");
    appendCell(row, candidate.mismatch_count);
    appendCell(row, candidate.seed_mismatches_count);
    appendCell(row, `${Number(candidate.cleavage_probability_percent).toFixed(3)}%`);
    appendCell(row, candidate.risk_level);
    body.appendChild(row);
  });

  byId("results").hidden = false;
  byId("download-button").disabled = false;
  setMessage("Assessment completed in the browser.", "success");
}

async function runAssessment(event) {
  event.preventDefault();
  if (!pyodideRuntime) {
    setMessage("The Python runtime is not ready.", "error");
    return;
  }

  const nuclease = byId("nuclease").value;
  const guideId = byId("guide-id").value.trim() || "GUIDE-001";
  const onTarget = byId("on-target").value.trim().toUpperCase();
  const candidates = readCandidateSequences().map((sequence) => sequence.toUpperCase());

  try {
    validateInputs(nuclease, onTarget, candidates);
    byId("run-button").disabled = true;
    byId("download-button").disabled = true;
    setMessage("Running the Python model…");

    pyodideRuntime.globals.set("BROWSER_NUCLEASE", nuclease);
    pyodideRuntime.globals.set("BROWSER_GUIDE_ID", guideId);
    pyodideRuntime.globals.set("BROWSER_ON_TARGET", onTarget);
    pyodideRuntime.globals.set("BROWSER_CANDIDATES_JSON", JSON.stringify(candidates));

    const resultJson = pyodideRuntime.runPython(
      "browser_assess(BROWSER_GUIDE_ID, BROWSER_ON_TARGET, BROWSER_NUCLEASE, BROWSER_CANDIDATES_JSON)"
    );
    renderResult(JSON.parse(String(resultJson)));
  } catch (error) {
    lastResult = null;
    byId("results").hidden = true;
    byId("download-button").disabled = true;
    setMessage(error instanceof Error ? error.message : String(error), "error");
  } finally {
    byId("run-button").disabled = false;
  }
}

function downloadResult() {
  if (!lastResult) {
    return;
  }
  const blob = new Blob([JSON.stringify(lastResult, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  const guideId = String(lastResult.guide_id || "guide").replace(/[^A-Za-z0-9._-]+/g, "_");
  anchor.href = url;
  anchor.download = `${guideId}-offtarget-assessment.json`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

async function initializePython() {
  try {
    setRuntimeStatus("Loading Python runtime…");
    pyodideRuntime = await loadPyodide({ indexURL: PYODIDE_INDEX_URL });

    const response = await fetch("./crispr_cas12_cas9.py", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Could not load Python engine (HTTP ${response.status}).`);
    }
    const source = await response.text();
    pyodideRuntime.globals.set("ENGINE_SOURCE", source);
    pyodideRuntime.runPython(`
import json

ENGINE_NS = {"__name__": "crispr_browser_engine"}
exec(ENGINE_SOURCE, ENGINE_NS)

def browser_assess(guide_id, on_target, nuclease, candidates_json):
    candidate_sequences = json.loads(candidates_json)
    candidates = [
        {"name": f"OT-{index + 1:02d}", "sequence": sequence}
        for index, sequence in enumerate(candidate_sequences)
    ]
    result = ENGINE_NS["CRISPRCas12Cas9Engine"].evaluate_guide(
        guide_id=str(guide_id),
        on_target_sequence=str(on_target),
        nuclease_type=str(nuclease),
        off_target_candidates=candidates,
    )
    return result.to_json()
`);

    setRuntimeStatus("Python ready", "ready");
    setMessage("Ready. Enter sequences and run an assessment.");
    byId("run-button").disabled = false;
  } catch (error) {
    pyodideRuntime = null;
    setRuntimeStatus("Runtime unavailable", "error");
    setMessage(
      `Browser Python initialization failed: ${error instanceof Error ? error.message : String(error)}`,
      "error"
    );
  }
}

function initializeUi() {
  byId("assessment-form").addEventListener("submit", runAssessment);
  byId("download-button").addEventListener("click", downloadResult);
  byId("example-button").addEventListener("click", loadExample);
  byId("nuclease").addEventListener("change", () => {
    const length = expectedLength(byId("nuclease").value);
    byId("sequence-help").textContent =
      `Use A/C/G/T only. The selected nuclease expects exactly ${length} nt.`;
  });
}

window.addEventListener("DOMContentLoaded", () => {
  initializeUi();
  initializePython();
});
