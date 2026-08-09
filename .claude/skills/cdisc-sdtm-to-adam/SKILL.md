---
name: cdisc-sdtm-to-adam
description: Claude Code adapter for the CDISC SDTM to ADaM Skill. Use when the user asks for CDISC Feasibility Checker, CDISC SDTM to ADaM Transfer, or a full CDISC SDTM to ADaM workflow from existing SDTM datasets and a concrete clinical or analysis objective, such as trial discontinuation, treatment-emergent adverse events, lab change from baseline, or exposure duration. Delegates shared runtime instructions to the repository-root SKILL.md.
---

# CDISC SDTM to ADaM Claude Code Adapter

This is the Claude Code-compatible entrypoint only. The repository-root `SKILL.md` is the canonical Codex Skill and shared source of truth.

After installing or reinstalling this Skill, output the canonical usage guide from `../../../SKILL.md` section `Post-Install Output`.

Invoke directly in Claude Code with:

```text
/cdisc-sdtm-to-adam
```

Or ask naturally, for example:

```text
Use CDISC SDTM to ADaM.

Objective: When and why do subjects discontinue the trial?
Available SDTM: DM, DS, SV, AE, EX, LB.

First check feasibility, show the derivation plan, and wait for confirmation before running the transfer.
```

Do not present examples where the objective is a dataset name, specification task, or derivation command such as `derive ADSL`, `build ADaM specs`, or `derive ADLB`.

Load and follow the canonical shared Skill definition at:

```text
../../../SKILL.md
```

Use the canonical standards scope reference at:

```text
../../../docs/standards/standards-index.md
```

Do not maintain duplicate runtime, derivation, validation, standards, evidence, or reporting instructions here.
