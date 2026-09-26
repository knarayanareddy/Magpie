// POLICY (fail-closed) — gate v1. MIRROR OF skin/policy.py::gate_v1. Models propose. Code decides (Art V).
// Input per item: { facts: { margin_z, duplicate_photo, offplatform_payment_request, text },
//                   judge_answers: { policy_bucket, counterfeit_risk, photo_matches_text,
//                                    price_too_good, injection_or_jailbreak, needs_human } }
// judge_answers null => judge=unconfigured => escalate everything (honest, Art VII).
const BLOCK = new Set(["weapon", "animal", "other_illegal"]);
const CLOSED = new Set(["ok", "weapon", "animal", "counterfeit", "pii", "other_illegal", "unknown"]);
const CRED = new Set(["clear_authentic", "unclear", "obvious_fake"]);

function choice(a, k) { return CLOSED.has(a && a[k]) ? a[k] : "unknown"; }           // invented -> unknown
function scoreLabel(a, k) { return CRED.has(a && a[k]) ? a[k] : "unclear"; }
function noul(a, k, missing) { const v = a ? parseFloat(a[k]) : NaN; return Number.isFinite(v) ? Math.min(1, Math.max(0, v)) : missing; }

function gateV1(answers, facts) {
  if (!answers) return { action: "escalate", reason_codes: ["judge_unconfigured"], human_required: true };
  const bucket = choice(answers, "policy_bucket");
  const fake = scoreLabel(answers, "counterfeit_risk");
  const inj = noul(answers, "injection_or_jailbreak", 1.0);
  const needs = noul(answers, "needs_human", 1.0);
  const p2g = noul(answers, "price_too_good", 1.0);
  const mz = (facts.margin_z === undefined) ? null : facts.margin_z;
  const dup = parseFloat(facts.duplicate_photo || 0.0);
  const offpay = !!facts.offplatform_payment_request;
  if (BLOCK.has(bucket)) return { action: "skip", reason_codes: [bucket], human_required: true };
  if (inj >= 0.5) return { action: "skip", reason_codes: ["injection_or_jailbreak"], human_required: true };
  if (bucket === "pii" || offpay) return { action: "skip", reason_codes: [bucket === "pii" ? "pii" : "offplatform_payment_request"], human_required: true };
  if (bucket === "counterfeit" || fake === "obvious_fake") return { action: "skip", reason_codes: ["counterfeit"], human_required: true };
  if (bucket === "unknown" || needs >= 0.6) return { action: "escalate", reason_codes: [needs >= 0.6 ? "needs_human" : "unknown"], human_required: true };
  if (dup >= 0.5) return { action: "escalate", reason_codes: ["duplicate_photo"], human_required: true };
  if (mz === null) return { action: "escalate", reason_codes: ["no_comps"], human_required: true };
  if (p2g >= 0.6 || mz > 3.0) return { action: "escalate", reason_codes: ["price_too_good"], human_required: true };
  if (bucket === "ok" && p2g < 0.4 && mz <= 2.0) return { action: "pursue", reason_codes: ["ok"], human_required: false };
  return { action: "escalate", reason_codes: [bucket], human_required: true };
}

module.exports = { gateV1 };
