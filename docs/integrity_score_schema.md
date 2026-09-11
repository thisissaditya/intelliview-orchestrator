# integrity_score schema (Issue #44)

Domain: Anti-cheat Signal Fusion
Files: workers/risk_engine.py
Label: anti-cheat

This document defines the 0–100 integrity_score, the meaning of each score range, the default weight breakdown for signals (tab-switch, gaze/face, risk), and the JSON schema that backend and frontend should consume.

## Overview

- integrity_score: integer in the range 0–100 (inclusive). Higher values indicate higher observed integrity (lower likelihood of cheating).
- Signals: three input signals that feed the integrity_score fusion:
  - tab_switch: client-side observation of tab/window/context switches.
  - gaze_face: camera-based attention and face-detection metrics (gaze, face present, occlusions).
  - risk: other risk signals from server-side detectors (answer similarity, suspicious patterns, keystroke anomalies, known heuristics).

The fusion algorithm itself (how to compute per-signal scores) is out of scope for this issue (see D3). This file documents the schema, normalization rules, default weights, and fallbacks.

## Score ranges and meaning

All ranges are inclusive of the lower bound and exclusive of the upper bound except the top range which includes 100.

- 0–20: Very low integrity — very high likelihood of cheating. Immediate human review recommended.
- 20–40: Low integrity — high likelihood of cheating. Escalate to flagging/heightened monitoring.
- 40–60: Medium integrity — ambiguous; may be acceptable but worth sampling or secondary checks.
- 60–80: High integrity — low likelihood of cheating; normal processing.
- 80–100: Very high integrity — strong evidence of integrity.

Notes:
- The team should agree whether thresholds are soft (recommended bands) or hard (triggers). This doc uses recommended bands; enforcement (e.g., auto-fail, block) must be defined separately.

## Default weight breakdown

Weights are floats that sum to 1.0. Default recommended weights:

- gaze_face: 0.45 (45%) — camera attention and face detection provide the strongest evidence of test-taker presence and attention when available.
- risk: 0.30 (30%) — server-side risk detectors capture behavioral and content-based signals complementary to camera data.
- tab_switch: 0.25 (25%) — tab/window switching is a clear signal but can be noisy (e.g., legitimate multitasking or accessibility tools).

Rationale: gaze/face receives the largest share due to high information content when camera is available and reliable. risk-models provide orthogonal signals (e.g., answer similarity) and get medium weight. tab-switch is important but more brittle, so lower weight.

### Configurability

- We recommend these weights be configurable per-exam via a server-side policy. Example per-exam overrides allow stricter or looser sensitivity.

### Fallbacks when a signal is missing/unreliable

If gaze_face is unavailable (camera off or blocked), redistribute its weight proportionally to the remaining signals by default. Example: if gaze_face unavailable, rescale weights to keep relative proportions between remaining signals:

- Original: gaze_face=0.45, risk=0.30, tab_switch=0.25
- Remaining signals sum = 0.30+0.25 = 0.55
- New risk weight = 0.30 / 0.55 ≈ 0.5455
- New tab_switch weight = 0.25 / 0.55 ≈ 0.4545

Optionally, implement a minimum-data policy: if fewer than N signals are available (N configurable, e.g., 2), mark integrity_score as 'insufficient_data' and require alternative handling (e.g., prompt proctor review).

## Normalization rules for signals

Each input signal must be normalized to a 0–100 scale where higher means higher integrity.

Signal-specific guidance (examples; exact extraction lives in D3):

- tab_switch
  - Basic metric: percent time focused on exam window or number of off-focus events per minute.
  - Example mapping:
    - 0 off-focus events/min -> 100
    - 1–2 off-focus events/min -> 80
    - 3–5 -> 50
    - >5 -> 10
  - Inverse relationship: more switches -> lower score.

- gaze_face
  - Use combination of face present (boolean), gaze-on-task proportion, and occlusion detection.
  - Example composite: face_present_score (0/100), gaze_attentiveness (0–100), occlusion_penalty (0–100); combine with weights internally to produce final 0–100.

- risk
  - Score from server risk models already on a 0–100 scale where higher = lower risk (if the model outputs risk, invert to map to integrity). Define mapping per model.

Important: Signals must be documented in their producing components so consumers know whether the reported signal is already normalized or needs transformation.

## Fusion formula (recommended)

Final integrity_score is the weighted sum of normalized component scores, rounded to the nearest integer:

integrity_score = round( sum_i ( weight_i * component_score_i ) )

where weights sum to 1.0 and component_score_i is in [0, 100].

Example: gaze_face=80 (0.45), risk=70 (0.30), tab_switch=60 (0.25)
score = round(0.45*80 + 0.30*70 + 0.25*60) = round(36 + 21 + 15) = 72

## JSON schema (example payload)

```json
{
  "version": "integrity_score.v1",
  "timestamp": "2026-09-06T12:34:56Z",
  "integrity_score": 72,
  "components": {
    "gaze_face": { "score": 80, "weight": 0.45, "raw": { /* producer-defined raw fields */ } },
    "risk": { "score": 70, "weight": 0.30, "raw": { /* producer-defined raw fields */ } },
    "tab_switch": { "score": 60, "weight": 0.25, "raw": { /* producer-defined raw fields */ } }
  },
  "notes": "weights used = default; gaze_face available",
  "policy": {
    "weight_overrides": null,
    "fallback": "rescaled"
  }
}
```

Consumer contract:
- integrity_score: integer 0–100; must be treated as authoritative summary for UI decisions, but follow policy for thresholds.
- components: each entry must include score (0–100) and weight (float). Consumers may display component breakdowns.
- raw: optional object included by producer for debugging/traceability; backends must not expose sensitive raw data in client UI.

## JSON Schema (Draft)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "IntegrityScore",
  "type": "object",
  "required": ["version","timestamp","integrity_score","components"],
  "properties": {
    "version": {"type":"string"},
    "timestamp": {"type":"string","format":"date-time"},
    "integrity_score": {"type":"integer","minimum":0,"maximum":100},
    "components": {
      "type":"object",
      "properties": {
        "gaze_face": {"$ref":"#/definitions/component"},
        "risk": {"$ref":"#/definitions/component"},
        "tab_switch": {"$ref":"#/definitions/component"}
      },
      "additionalProperties": true
    },
    "notes": {"type":"string"},
    "policy": {"type":"object"}
  },
  "definitions": {
    "component": {
      "type":"object",
      "required":["score","weight"],
      "properties":{
        "score":{"type":"integer","minimum":0,"maximum":100},
        "weight":{"type":"number","minimum":0,"maximum":1},
        "raw":{"type":"object"}
      }
    }
  }
}
```

## Implementation guidance for workers/risk_engine.py

- Expose a function (or class) that accepts normalized component scores and returns the integrity_score using the formula above. Do not implement the normalization itself here — accept pre-normalized component scores.
- Provide configuration hooks for per-exam weight overrides and fallback policy.
- Emit the JSON payload above to the event stream and include `raw` only in internal logs or in secure backend-to-backend channels.

## Acceptance criteria (this issue)

- [x] Documented 0–100 integrity_score schema with defined score ranges.
- [x] Default weight breakdown provided and rationale explained.
- [x] JSON schema and example payload included for backend/frontend consumption.
- [ ] Team review and agreement (please review and comment on PR or this document).

---

If you'd like, I can:
- Open a PR with this document and link the issue (recommended),
- Add a small helper function stub in workers/risk_engine.py that consumes normalized signals and applies the weights (no fusion/normalization), or
- Propose UI/threshold values for automated actions.
