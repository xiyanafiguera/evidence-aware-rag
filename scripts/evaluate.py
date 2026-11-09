"""Evaluate retrieval modes on a question split and write the results to results/.

Usage:
    uv run scripts/evaluate.py                       # dev split, all available modes
    uv run scripts/evaluate.py --methods bm25,hybrid
    uv run scripts/evaluate.py --split heldout --final   # run ONCE, after freezing parameters

The held-out split refuses to run on a dirty git tree or if results already exist, and records the
commit it was run on.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import subprocess
import sys
from datetime import datetime, timezone

from pydantic import TypeAdapter

from evidence_aware_rag.evaluation import score_question, summarize, summarize_by_category
from evidence_aware_rag.models import Question
from evidence_aware_rag.pipeline import MODES, KnowledgeBase, build_pipeline


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def fmt_count(pair: list[int] | tuple[int, int]) -> str:
    hit, total = pair
    return f"{hit}/{total}" if total else "—"


def fmt(value) -> str:
    return "—" if value is None else f"{value:.2f}"


def render_markdown(split: str, run_info: dict, summaries: dict, by_category: dict, per_question: dict) -> str:
    lines = [f"# Results — {split} split", "",
             f"Commit `{run_info['commit']}` · {run_info['timestamp']} · {run_info['questions']} questions", "",
             "## Ranking (retrieved list before expansion, same k for all modes)", "",
             "| Mode | Recall@3 | Recall@5 | MRR | All gold docs in top-5 |",
             "|------|----------|----------|-----|------------------------|"]
    for mode, s in summaries.items():
        lines.append(f"| {mode} | {fmt(s['recall_at_3'])} | {fmt(s['recall_at_5'])} | {fmt(s['mrr'])} "
                     f"| {fmt_count(s['complete_ranking_at_5'])} |")
    lines += ["", "## Evidence package", "",
              "| Mode | All gold docs in package | Avg package size | Correct version + reason | Ambiguity flags correct "
              "| Unanswerable → insufficient / unknown / sufficient | False 'insufficient' on answerable |",
              "|------|---|---|---|---|---|---|"]
    for mode, s in summaries.items():
        u = s["unanswerable"]
        lines.append(f"| {mode} | {fmt_count(s['complete_package'])} | {s['avg_package_size']} "
                     f"| {fmt_count(s['version_correct'])} | {fmt_count(s['flags_correct'])} "
                     f"| {u['insufficient']} / {u['unknown']} / {u['sufficient']} (of {u['total']}) "
                     f"| {s['false_insufficient_on_answerable']} |")
    lines += ["", "## By category (all gold docs in top-5 ranking / in package)", "",
              "| Category | " + " | ".join(summaries) + " |",
              "|---|" + "---|" * len(summaries)]
    categories = sorted({c for per_mode in by_category.values() for c in per_mode})
    for category in categories:
        cells = []
        for mode in summaries:
            s = by_category[mode][category]
            cells.append(f"{fmt_count(s['complete_ranking_at_5'])} / {fmt_count(s['complete_package'])}")
        lines.append(f"| {category} | " + " | ".join(cells) + " |")
    lines += ["", "## Per question", "",
              "| ID | Category | " + " | ".join(f"{m}: ranking top-5" for m in summaries) + " |",
              "|---|---|" + "---|" * len(summaries)]
    ids = list(next(iter(per_question.values())).keys())
    for qid in ids:
        first = next(iter(per_question.values()))[qid]
        cells = [", ".join(per_question[m][qid]["ranking"][:5]) for m in summaries]
        lines.append(f"| {qid} | {first['category']} | " + " | ".join(cells) + " |")
    lines += ["", "Counts are absolute (hits/total). The dataset is small and synthetic: these numbers "
              "describe this prototype, they are not a benchmark."]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", choices=["dev", "heldout"], default="dev")
    parser.add_argument("--methods", default=",".join(MODES))
    parser.add_argument("--final", action="store_true", help="required for the held-out split")
    args = parser.parse_args()

    kb = KnowledgeBase.load()
    out_json = kb.settings.results_dir / f"metrics_{args.split}.json"
    out_md = kb.settings.results_dir / f"RESULTS_{args.split}.md"
    if args.split == "heldout":
        if not args.final:
            sys.exit("the held-out split is evaluated once: pass --final to confirm")
        if out_json.exists():
            sys.exit(f"{out_json} already exists: the held-out split must not be re-run")
        if git("status", "--porcelain", "--untracked-files=no"):
            sys.exit("working tree has uncommitted changes: commit first so the run is traceable")

    questions = TypeAdapter(list[Question]).validate_json(
        (kb.settings.eval_dir / f"questions_{args.split}.json").read_text(encoding="utf-8")
    )
    modes = [m.strip() for m in args.methods.split(",") if m.strip()]

    summaries, by_category, per_question = {}, {}, {}
    for mode in modes:
        try:
            pipeline = build_pipeline(mode, kb)
        except NotImplementedError as exc:
            print(f"skipping {mode}: {exc}")
            continue
        results = [score_question(pipeline.run(q.question), q, kb.corpus) for q in questions]
        summaries[mode] = summarize(results)
        by_category[mode] = summarize_by_category(results)
        per_question[mode] = {r.id: r.model_dump() for r in results}

    run_info = {
        "split": args.split,
        "commit": git("rev-parse", "--short", "HEAD"),
        "dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "questions": len(questions),
        "settings": {k: str(v) for k, v in dataclasses.asdict(kb.settings).items() if not k.endswith("_dir") and k != "root"},
    }
    kb.settings.results_dir.mkdir(exist_ok=True)
    out_json.write_text(json.dumps({"run": run_info, "summary": summaries, "by_category": by_category,
                                    "per_question": per_question}, indent=2), encoding="utf-8")
    out_md.write_text(render_markdown(args.split, run_info, summaries, by_category, per_question), encoding="utf-8")
    print(out_md.read_text(encoding="utf-8") if args.split == "dev" else f"written {out_json} and {out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
