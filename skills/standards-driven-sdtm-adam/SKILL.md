---
name: standards-driven-sdtm-adam
description: Codex adapter for the CDISC SDTM to ADaM Skill. Use when the user asks for CDISC Feasibility Checker, CDISC SDTM to ADaM Transfer, or a full CDISC SDTM to ADaM workflow from existing SDTM datasets and a concrete clinical or analysis objective, such as trial discontinuation, treatment-emergent adverse events, lab change from baseline, or exposure duration. Delegates shared runtime instructions to the repository-root SKILL.md.
---

# CDISC SDTM to ADaM Codex Adapter

This is the Codex-compatible entrypoint only.

Load and follow the canonical shared Skill definition at:

```text
../../SKILL.md
```

Use the canonical standards scope reference at:

```text
../../docs/standards/standards-index.md
```

Preserve Codex-specific metadata in `agents/openai.yaml`. Do not maintain duplicate runtime, derivation, validation, standards, evidence, or reporting instructions here.
