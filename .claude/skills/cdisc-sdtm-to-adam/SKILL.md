---
name: cdisc-sdtm-to-adam
description: Claude Code adapter for the CDISC SDTM to ADaM Skill. Use when the user asks to create ADSL, ADAE, ADLB, or ADTTE from existing SDTM datasets, asks whether an ADaM objective is feasible, or asks for a standards-driven SDTM-to-ADaM derivation workflow in this repository. Delegates shared runtime instructions to skill/standards-driven-sdtm-to-adam/SKILL.md.
---

# CDISC SDTM to ADaM Claude Code Adapter

This is the Claude Code-compatible entrypoint only. It does not replace the Codex adapter in `skills/standards-driven-sdtm-adam`.

Invoke directly in Claude Code with:

```text
/cdisc-sdtm-to-adam
```

Or ask naturally, for example:

```text
Use the CDISC SDTM to ADaM skill.

I have attached my SDTM datasets.

Goal:
Create ADSL and ADAE.

Check feasibility first. If the objective is supported,
build the derivation plan, derive the datasets,
run independent validation, and return the traceability report.
```

Load and follow the canonical shared Skill definition at:

```text
../../../skill/standards-driven-sdtm-to-adam/SKILL.md
```

Use the canonical standards scope reference at:

```text
../../../skill/standards-driven-sdtm-to-adam/references/standards-index.md
```

Do not maintain duplicate runtime, derivation, validation, standards, evidence, or reporting instructions here.
