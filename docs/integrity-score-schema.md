# Anti-cheat `integrity_score` schema (D2)

This is the canonical contract for the anti-cheat signal fusion score. The
schema is intentionally independent of UI styling: consumers should use the
numeric score and the ranges below, not infer meaning from a color or label.

## Field contract

| Field | Type | Range | Meaning |
| --- | --- | --- | --- |
| `integrity_score` | integer | `0`-`100` inclusive | Overall interview integrity; higher is better |

`100` means no suspicious activity was observed in the available signals.
`0` means the full combined penalty was observed. The score is clamped to the
declared range and is never negative or greater than 100.

## Signal weight breakdown

The score has a 100-point penalty budget:

| Signal | Weight | Maximum penalty | Input meaning |
| --- | ---: | ---: | --- |
| `tab_switch` | 20% | 20 points | Suspicious focus changes or tab switches |
| `gaze_face` | 30% | 30 points | Gaze deviation, missing face, or other face-presence anomalies |
| `risk` | 50% | 50 points | Normalized risk-engine result (`0.0` = no risk, `1.0` = maximum risk) |

The names above are the aggregate contract names. Existing pipeline-specific
signals may be mapped into these aggregates, but the mapping must not change
their weight or polarity: more suspicious activity always lowers the score.

## Score interpretation

Ranges are inclusive and intentionally non-overlapping:

| Score | Meaning | Operational interpretation |
| ---: | --- | --- |
| `90-100` | Trusted | No or only negligible anti-cheat evidence |
| `75-89` | Low concern | Minor isolated signal; normally no manual action |
| `50-74` | Review recommended | Meaningful evidence; review the supporting signals |
| `25-49` | High concern | Multiple or material signals; manual review expected |
| `0-24` | Critical concern | Strong evidence of integrity issues; follow escalation policy |

The range is an interpretation aid, not an automatic hiring or rejection
decision. Frontend consumers may display a label, but the numeric value and
supporting signals remain authoritative.

## Missing and partial data

Missing signals must not be interpreted as suspicious activity. A consumer
should mark unavailable components as unavailable and avoid inventing a
zero-value observation. A score calculated from partial data should be
accompanied by the component availability in the containing response when
that metadata is available.

If no usable anti-cheat signal is available, the backend should use the
neutral `100` value only when the response explicitly indicates that the
score is based on no observed risk; it must not be presented as proof that
the interview was fully verified.

## Review gate

This document is the D2 design contract. Backend and frontend owners must
agree on the field name, weights, score bands, polarity, and missing-data
rules before changing or extending the fusion implementation (D3). Changes
to this contract require updating this document and the corresponding
consumer tests together.
