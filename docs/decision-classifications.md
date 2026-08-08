# Decision Classifications

Version 1 uses exactly these decision classifications:

- `STANDARD_REQUIRED`: Required by primary standard evidence for the applicable scope.
- `STANDARD_GUIDED`: Guided by standard evidence, but implementation still depends on source data and study context.
- `STUDY_SPECIFIC`: Requires an explicit study decision; standards do not define the final choice.
- `USER_DEFINED`: Supplied by the user or study team rather than inferred from standards.
- `DATA_ENGINEERING`: Technical handling that preserves source meaning and does not claim a CDISC derivation requirement.
- `EXAMPLE_ADAPTED`: Adapted from example or validation-reference material; examples are not mandatory rules.
- `UNSUPPORTED`: Not supported for Version 1 implementation.

Do not add classifications without an explicit scope change. Classification occurs before implementation, and implementation must not be used to backfill or invent classification rationale.
