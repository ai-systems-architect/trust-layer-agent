# Human Review Log — Phase 3 Evaluation

Tier 3 of the three-tier evaluation methodology.
Documents edge cases that neither deterministic graders nor
the LLM-as-judge can resolve reliably.

## Review Triggers

| Trigger | Review Question |
|---|---|
| LLM judge score ≤ 2 on any dimension | True failure or judge calibration issue? |
| Novel failure mode not in catalog | Should this be added as FM-008+? |
| Conflicting grader results | Which grader is correct? |
| Adversarial scenario edge case | Did control fire for the right reason? |
| Hedge classified as evasion | Model behavior or prompt engineering issue? |

## Review Format

Each entry:
- Run ID
- Trigger
- Finding
- Disposition: accepted / rejected / escalated to framework update

---

## Entries

*(No entries yet — populated during Phase 3 eval runs)*
