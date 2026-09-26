// POLICY (fail-closed) — gate v0. MIRROR OF skin/policy.py::gate_v0. Models propose. Code decides (Art V).
// Parity rule (Art II.4): any edit here must be mirrored in skin/policy.py and vice versa.
// Run app/tests/test_gate_parity.py after edits. Paste this function into the n8n Code node (or import wf-m0).
const ILLEGAL_RE = /\b(weapon|knife|knives|gun|pistol|ammo|hunting knife|airsoft)\b/i;
const INJECTION = ["ignore previous instructions", "accept any offer", "mark as sold", "mark as safe", "disregard all prior"];
const ADVANCE_FEE = /(iban|nl\d{2}[A-Z]{4}\d{4,}|tikkie|paypal\.me|pay (in advance|to reserve)|transfer €?\d+)/i;

function gateV0(facts) {
  const mz = (facts.margin_z === undefined) ? null : facts.margin_z;
  const text = String(facts.text || "").toLowerCase();
  if (INJECTION.some(p => text.includes(p))) return { action: "skip", reason_codes: ["injection_or_jailbreak"], human_required: true };
  if (ILLEGAL_RE.test(text)) return { action: "skip", reason_codes: ["illegal_keyword"], human_required: true };
  if (facts.offplatform_payment_request || ADVANCE_FEE.test(text)) return { action: "skip", reason_codes: ["offplatform_payment_request"], human_required: true };
  if (mz === null) return { action: "escalate", reason_codes: ["no_comps"], human_required: true };
  if (mz > 2.5) return { action: "escalate", reason_codes: ["price_too_good"], human_required: true };
  if (mz > 0 && mz <= 2.5) return { action: "pursue", reason_codes: ["ok"], human_required: false };
  return { action: "escalate", reason_codes: ["no_margin"], human_required: true };  // mz <= 0: asking at or above comps — no deal
}

module.exports = { gateV0 };

// ---- n8n Code node usage (items = incoming JSON) ----
// const { gateV0 } = module.exports ? module.exports : {};
// items = items.map(it => { const g = gateV0(it.json.facts); return { json: { ...it.json, gate: g } }; });
