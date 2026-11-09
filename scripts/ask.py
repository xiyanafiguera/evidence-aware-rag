"""Print the evidence package for one question (demo and debugging).

Usage:
    uv run scripts/ask.py "What compensation is Acme Corp entitled to for INC-014?"
    uv run scripts/ask.py "..." --mode hybrid --as-of 2026-11-10 --json
"""

from __future__ import annotations

import argparse
from datetime import date

from evidence_aware_rag.pipeline import MODES, KnowledgeBase, build_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("question")
    parser.add_argument("--mode", choices=MODES, default="full")
    parser.add_argument("--as-of", type=date.fromisoformat, default=None)
    parser.add_argument("--json", action="store_true", help="print the raw EvidencePackage")
    args = parser.parse_args()

    package = build_pipeline(args.mode, KnowledgeBase.load()).run(args.question, as_of=args.as_of)
    if args.json:
        print(package.model_dump_json(indent=2))
        return

    print(f"\nQ: {package.query}\nmode: {package.method} · intent: {package.intent or '—'}\n")
    for t in package.temporal:
        print(f"[{t.policy_family}] {t.governed_by}: {', '.join(t.applicable) or '—'}")
        print(f"    {t.justification}")
        if t.ambiguity_detected:
            print(f"    ambiguity: candidates {[c.document_id for c in t.candidate_interpretations]}, "
                  f"clarification needed: {t.clarification_needed}")
        for note in t.date_notes:
            print(f"    note: {note}")
    s = package.sufficiency
    print(f"\nsufficiency: {s.status}{' (missing: ' + ', '.join(s.missing) + ')' if s.missing else ''}\n    {s.reason}\n")
    print("evidence:")
    for item in package.evidence:
        status = f" [{item.version_status}]" if item.version_status != "n/a" else ""
        print(f"  {item.document_id}{status} {item.title}")
        for reason in item.why_included:
            print(f"      · {reason}")


if __name__ == "__main__":
    main()
