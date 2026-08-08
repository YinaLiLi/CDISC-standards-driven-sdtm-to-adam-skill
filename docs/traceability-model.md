# Traceability Model

Version 1 preserves traceability through explicit stage outputs:

```text
source SDTM data
  -> extracted standards evidence
  -> classified specification item
  -> preprocessing or derivation execution record
  -> independent validation result
  -> resolved citation
  -> deterministic report
```

Not every stage has standard evidence. Study-specific, user-defined, data-engineering, example-adapted, and unsupported decisions retain their classification semantics rather than receiving fabricated normative citations.

Evidence resolution produces:

- resolved citations
- unresolved evidence references
- excluded evidence references

Reports consume those resolved outputs directly and do not re-resolve evidence.
