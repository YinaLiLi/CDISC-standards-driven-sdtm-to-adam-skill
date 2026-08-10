"""Compile configured local standards into a versioned Knowledge Pack."""

from __future__ import annotations

import argparse
from pathlib import Path

from standards_driven_sdtm_adam.knowledge.compiler import KnowledgePackCompiler


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry-dir", required=True, help="Directory containing standards manifest YAML files.")
    parser.add_argument("--output-root", default="knowledge", help="Knowledge Pack output directory.")
    parser.add_argument("--pack-version", default="local-unreviewed", help="Knowledge Pack version label.")
    args = parser.parse_args()

    output = KnowledgePackCompiler.from_registry_dir(args.registry_dir).write_semantic_reconstruction(
        Path(args.output_root),
        pack_version=args.pack_version,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
