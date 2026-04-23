from __future__ import annotations

import argparse
import csv
import json
import logging
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
DEFAULT_MODELS = ["gpt-41-mini", "gpt-5-mini", "gpt-51"]
DEFAULT_DATASET_TYPES = ["city_council", "private_data"]
LEGACY_FIELDNAMES = [
    "row_type",
    "dataset_type",
    "meeting_id",
    "candidate_model",
    "deepeval_accuracy",
    "deepeval_coverage",
    "accuracy_reason",
    "coverage_reason",
    "candidate_path",
    "gt_path",
    "note",
]
FIELDNAMES = [
    "row_type",
    "dataset_type",
    "meeting_id",
    "candidate_model",
    "deepeval_holistic_accuracy",
    "deepeval_holistic_coverage",
    "system_accuracy",
    "system_completeness",
    "system_coverage",
    "holistic_accuracy_delta_vs_system",
    "holistic_coverage_delta_vs_system",
    "accuracy_reason",
    "coverage_reason",
    "candidate_path",
    "gt_path",
    "report_path",
    "note",
]


@dataclass(frozen=True)
class MeetingModelPair:
    meeting_id: str
    dataset_type: str
    candidate_model: str
    system_accuracy: float
    system_completeness: float
    system_coverage: float
    report_path: str


def resolve_default_combined_csv() -> Path:
    candidates = [
        PROJECT_ROOT / "paper" / "meeting_notes_model_comparison_combined_20260417.csv",
        PROJECT_ROOT
        / "report"
        / "whitehouse_press_briefings_20260416_merged"
        / "meeting_notes_model_comparison_combined_20260417.csv",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("Could not locate the merged benchmark CSV in paper/ or report/.")


def resolve_default_output_csv() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return PROJECT_ROOT / "report" / f"deepeval_typed_empirical_comparison_{timestamp}.csv"


def ensure_openai_compatible_env() -> None:
    os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "true")

    if os.getenv("OPENAI_API_KEY") and (os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")):
        return

    try:
        from dotenv import dotenv_values
    except ImportError:
        return

    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    values = dotenv_values(env_path)
    llm_api_key = values.get("LLM_API_KEY")
    llm_api_base = values.get("LLM_API_BASE")
    if llm_api_key and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = llm_api_key
    if llm_api_base:
        if not os.getenv("OPENAI_BASE_URL"):
            os.environ["OPENAI_BASE_URL"] = llm_api_base
        if not os.getenv("OPENAI_API_BASE"):
            os.environ["OPENAI_API_BASE"] = llm_api_base


def resolve_meeting_paths(
    dataset_root: Path,
    meeting_id: str,
    candidate_model: str,
    candidate_variant: str,
    candidate_version: str,
) -> dict[str, Path]:
    return {
        "transcript_path": dataset_root / "assets" / "transcripts" / "internal" / meeting_id / "original_transcript.txt",
        "gt_path": dataset_root
        / "views"
        / "meeting_notes"
        / "ground_truth"
        / "internal"
        / meeting_id
        / "meetingsummary"
        / "ground_truth.json",
        "candidate_path": dataset_root
        / "views"
        / "meeting_notes"
        / "candidate"
        / "internal"
        / meeting_id
        / candidate_variant
        / candidate_model
        / candidate_version,
    }


def load_pairs(
    combined_csv_path: Path,
    dataset_types: set[str],
    candidate_models: Iterable[str],
    max_meetings_per_type: int | None = None,
) -> list[MeetingModelPair]:
    allowed_models = set(candidate_models)
    rows: list[dict] = []
    with combined_csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("row_type") != "meeting_model":
                continue
            if row.get("dataset_type") not in dataset_types:
                continue
            if row.get("candidate_model") not in allowed_models:
                continue
            rows.append(row)

    if max_meetings_per_type is not None:
        selected_by_type: dict[str, set[str]] = defaultdict(set)
        filtered: list[dict] = []
        for row in rows:
            dataset_type = row["dataset_type"]
            meeting_id = row["meeting_id"]
            if meeting_id in selected_by_type[dataset_type] or len(selected_by_type[dataset_type]) < max_meetings_per_type:
                selected_by_type[dataset_type].add(meeting_id)
                filtered.append(row)
        rows = filtered

    return [
        MeetingModelPair(
            meeting_id=row["meeting_id"],
            dataset_type=row["dataset_type"],
            candidate_model=row["candidate_model"],
            system_accuracy=float(row["accuracy_avg"]),
            system_completeness=float(row["completeness_avg"]),
            system_coverage=float(row["coverage_avg"]),
            report_path=row.get("report_path", ""),
        )
        for row in rows
    ]


def build_gt_reference_markdown(gt_path: Path) -> str:
    import sys

    if str(SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(SRC_ROOT))
    from evaluation.evaluation_utils import EvaluationUtils

    gt_raw = gt_path.read_text(encoding="utf-8")
    cleaned_gt = EvaluationUtils.cleanup_ground_truth(
        gt_raw,
        keep_decisions=True,
        keep_topics=True,
    )
    gt_json = json.loads(cleaned_gt)
    gt_json = EvaluationUtils.append_id_to_raw_gt(gt_json)
    return EvaluationUtils.json_to_markdown(gt_json)


def instantiate_metrics(evaluation_model: str):
    try:
        from deepeval.metrics import GEval
        from deepeval.test_case import LLMTestCaseParams
    except ImportError as exc:
        raise RuntimeError(
            "DeepEval is not installed. Install `deepeval` to run this example."
        ) from exc

    accuracy_metric = GEval(
        name="holistic_reference_accuracy",
        criteria=(
            "Judge whether the actual meeting summary is globally faithful to the expected ground truth. "
            "Reward coherent, transcript-grounded summaries; penalize contradictions, unsupported additions, "
            "fabricated details, and unjustified certainty."
        ),
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT],
        model=evaluation_model,
    )
    coverage_metric = GEval(
        name="holistic_reference_coverage",
        criteria=(
            "Judge how well the actual meeting summary covers the important information in the expected ground truth. "
            "Reward summaries that mention major actions, dates, decisions, and quantities; penalize material omissions."
        ),
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT],
        model=evaluation_model,
    )
    return accuracy_metric, coverage_metric


def normalize_existing_row(row: dict, pair_lookup: dict[tuple[str, str], MeetingModelPair]) -> dict | None:
    if row.get("row_type") != "meeting_model":
        return None
    meeting_id = row.get("meeting_id", "")
    model = row.get("candidate_model", "")
    pair = pair_lookup.get((meeting_id, model))
    if not pair:
        return None
    # Support both old and new schema.
    holistic_accuracy = row.get("deepeval_holistic_accuracy") or row.get("deepeval_accuracy") or ""
    holistic_coverage = row.get("deepeval_holistic_coverage") or row.get("deepeval_coverage") or ""
    accuracy_reason = row.get("accuracy_reason", "")
    coverage_reason = row.get("coverage_reason", "")
    return {
        "row_type": "meeting_model",
        "dataset_type": pair.dataset_type,
        "meeting_id": meeting_id,
        "candidate_model": model,
        "deepeval_holistic_accuracy": holistic_accuracy,
        "deepeval_holistic_coverage": holistic_coverage,
        "system_accuracy": f"{pair.system_accuracy:.3f}",
        "system_completeness": f"{pair.system_completeness:.3f}",
        "system_coverage": f"{pair.system_coverage:.3f}",
        "holistic_accuracy_delta_vs_system": (
            f"{(float(holistic_accuracy) - pair.system_accuracy):+.3f}" if holistic_accuracy else ""
        ),
        "holistic_coverage_delta_vs_system": (
            f"{(float(holistic_coverage) - pair.system_coverage):+.3f}" if holistic_coverage else ""
        ),
        "accuracy_reason": accuracy_reason,
        "coverage_reason": coverage_reason,
        "candidate_path": row.get("candidate_path", ""),
        "gt_path": row.get("gt_path", ""),
        "report_path": pair.report_path,
        "note": row.get("note", ""),
    }


def normalize_existing_raw_row(raw_row: list[str], pair_lookup: dict[tuple[str, str], MeetingModelPair]) -> dict | None:
    if not raw_row:
        return None

    if len(raw_row) >= len(FIELDNAMES):
        row = {FIELDNAMES[idx]: raw_row[idx] for idx in range(len(FIELDNAMES))}
        return normalize_existing_row(row, pair_lookup)

    if len(raw_row) >= len(LEGACY_FIELDNAMES):
        row = {LEGACY_FIELDNAMES[idx]: raw_row[idx] for idx in range(len(LEGACY_FIELDNAMES))}
        return normalize_existing_row(row, pair_lookup)

    return None


def load_existing_progress(
    output_path: Path,
    pair_lookup: dict[tuple[str, str], MeetingModelPair],
) -> tuple[list[dict], set[tuple[str, str]], dict[tuple[str, str], dict[str, float]]]:
    rows: list[dict] = []
    completed: set[tuple[str, str]] = set()
    aggregate: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: {"count": 0, "holistic_accuracy_sum": 0.0, "holistic_coverage_sum": 0.0}
    )

    if not output_path.exists():
        return rows, completed, aggregate

    with output_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        _header = next(reader, None)
        for raw_row in reader:
            row = normalize_existing_raw_row(raw_row, pair_lookup)
            if not row:
                continue
            rows.append(row)
            key = (row["meeting_id"], row["candidate_model"])
            completed.add(key)
            agg_key = (row["dataset_type"], row["candidate_model"])
            aggregate[agg_key]["count"] += 1
            aggregate[agg_key]["holistic_accuracy_sum"] += float(row["deepeval_holistic_accuracy"] or 0.0)
            aggregate[agg_key]["holistic_coverage_sum"] += float(row["deepeval_holistic_coverage"] or 0.0)

    return rows, completed, aggregate


def write_csv(output_path: Path, rows: list[dict]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def append_csv_row(output_path: Path, row: dict) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_path.exists() and output_path.stat().st_size > 0
    with output_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in FIELDNAMES})


def finalize_output_csv(
    output_path: Path,
    meeting_rows: list[dict],
    aggregate: dict[tuple[str, str], dict[str, float]],
    pair_lookup: dict[tuple[str, str], MeetingModelPair],
) -> None:
    final_rows = [row for row in meeting_rows if row.get("row_type") == "meeting_model"]
    for (dataset_type, candidate_model), stats in sorted(aggregate.items()):
        count = int(stats["count"])
        if count == 0:
            continue
        # derive system means from pair lookup for the completed subset
        completed_pairs = [
            pair
            for pair in pair_lookup.values()
            if pair.dataset_type == dataset_type and pair.candidate_model == candidate_model
        ]
        if count:
            system_accuracy = sum(pair.system_accuracy for pair in completed_pairs) / len(completed_pairs)
            system_completeness = sum(pair.system_completeness for pair in completed_pairs) / len(completed_pairs)
            system_coverage = sum(pair.system_coverage for pair in completed_pairs) / len(completed_pairs)
        else:
            system_accuracy = system_completeness = system_coverage = 0.0
        holistic_accuracy = stats["holistic_accuracy_sum"] / count
        holistic_coverage = stats["holistic_coverage_sum"] / count
        final_rows.append(
            {
                "row_type": "model_summary_dataset_type",
                "dataset_type": dataset_type,
                "meeting_id": "",
                "candidate_model": candidate_model,
                "deepeval_holistic_accuracy": f"{holistic_accuracy:.3f}",
                "deepeval_holistic_coverage": f"{holistic_coverage:.3f}",
                "system_accuracy": f"{system_accuracy:.3f}",
                "system_completeness": f"{system_completeness:.3f}",
                "system_coverage": f"{system_coverage:.3f}",
                "holistic_accuracy_delta_vs_system": f"{(holistic_accuracy - system_accuracy):+.3f}",
                "holistic_coverage_delta_vs_system": f"{(holistic_coverage - system_coverage):+.3f}",
                "accuracy_reason": "",
                "coverage_reason": "",
                "candidate_path": "",
                "gt_path": "",
                "report_path": "",
                "note": f"meeting_count={count}",
            }
        )
    write_csv(output_path, final_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a resumable DeepEval baseline over typed benchmark slices and store "
            "standardized semantic columns alongside the repository's structured metrics."
        )
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=PROJECT_ROOT / "dataset",
        help="Dataset root containing transcripts, GT, candidates, and evaluation artifacts.",
    )
    parser.add_argument(
        "--combined-csv",
        type=Path,
        default=resolve_default_combined_csv(),
        help="Merged benchmark CSV used to select meeting-model pairs.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=resolve_default_output_csv(),
        help="Destination CSV for per-pair and per-model results.",
    )
    parser.add_argument(
        "--candidate-variant",
        default="standard",
        help="Candidate summary style / variant.",
    )
    parser.add_argument(
        "--candidate-version",
        default="baseline.md",
        help="Candidate filename under each model directory.",
    )
    parser.add_argument(
        "--dataset-types",
        nargs="+",
        default=DEFAULT_DATASET_TYPES,
        help="Dataset types to evaluate.",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        help="Candidate models to compare.",
    )
    parser.add_argument(
        "--evaluation-model",
        default="gpt-4.1-mini",
        help="Evaluator model passed through to DeepEval's GEval.",
    )
    parser.add_argument(
        "--max-meetings-per-type",
        type=int,
        default=None,
        help="Optional cap on unique meetings per dataset type.",
    )
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Resume from an existing output CSV by skipping completed meeting-model pairs.",
    )
    parser.add_argument(
        "--continue-on-error",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Log pair-level DeepEval errors and continue so unfinished pairs can be resumed later.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    ensure_openai_compatible_env()

    dataset_types = set(args.dataset_types)
    pairs = load_pairs(
        combined_csv_path=args.combined_csv,
        dataset_types=dataset_types,
        candidate_models=args.models,
        max_meetings_per_type=args.max_meetings_per_type,
    )
    pair_lookup = {(pair.meeting_id, pair.candidate_model): pair for pair in pairs}

    logging.info(
        "Loaded %d meeting-model pairs for dataset types %s from %s",
        len(pairs),
        ",".join(sorted(dataset_types)),
        args.combined_csv,
    )

    existing_rows, completed_pairs, aggregate = (
        load_existing_progress(args.output_csv, pair_lookup)
        if args.resume
        else ([], set(), defaultdict(lambda: {"count": 0, "holistic_accuracy_sum": 0.0, "holistic_coverage_sum": 0.0}))
    )
    output_rows: list[dict] = list(existing_rows)
    if completed_pairs:
        logging.info(
            "Resuming from %s with %d completed meeting-model pairs already recorded.",
            args.output_csv,
            len(completed_pairs),
        )

    try:
        from deepeval.test_case import LLMTestCase
    except ImportError as exc:
        raise SystemExit("DeepEval is not installed in this environment.") from exc

    for idx, pair in enumerate(pairs, start=1):
        key = (pair.meeting_id, pair.candidate_model)
        if args.resume and key in completed_pairs:
            logging.info("[%d/%d] %s %s -> skipped_existing", idx, len(pairs), pair.meeting_id, pair.candidate_model)
            continue

        paths = resolve_meeting_paths(
            args.dataset_root,
            pair.meeting_id,
            pair.candidate_model,
            args.candidate_variant,
            args.candidate_version,
        )
        transcript = paths["transcript_path"].read_text(encoding="utf-8")
        candidate = paths["candidate_path"].read_text(encoding="utf-8")
        reference_markdown = build_gt_reference_markdown(paths["gt_path"])
        test_case = LLMTestCase(input=transcript, actual_output=candidate, expected_output=reference_markdown)

        accuracy_metric, coverage_metric = instantiate_metrics(args.evaluation_model)
        try:
            accuracy_metric.measure(test_case)
            coverage_metric.measure(test_case)
        except Exception as exc:  # noqa: BLE001
            logging.exception(
                "[%d/%d] %s %s %s -> deepeval_failed: %s",
                idx,
                len(pairs),
                pair.dataset_type,
                pair.meeting_id,
                pair.candidate_model,
                exc,
            )
            if args.continue_on_error:
                continue
            raise

        holistic_accuracy = float(getattr(accuracy_metric, "score", 0.0) or 0.0)
        holistic_coverage = float(getattr(coverage_metric, "score", 0.0) or 0.0)
        accuracy_reason = getattr(accuracy_metric, "reason", "")
        coverage_reason = getattr(coverage_metric, "reason", "")

        agg_key = (pair.dataset_type, pair.candidate_model)
        aggregate[agg_key]["count"] += 1
        aggregate[agg_key]["holistic_accuracy_sum"] += holistic_accuracy
        aggregate[agg_key]["holistic_coverage_sum"] += holistic_coverage

        row = {
            "row_type": "meeting_model",
            "dataset_type": pair.dataset_type,
            "meeting_id": pair.meeting_id,
            "candidate_model": pair.candidate_model,
            "deepeval_holistic_accuracy": f"{holistic_accuracy:.3f}",
            "deepeval_holistic_coverage": f"{holistic_coverage:.3f}",
            "system_accuracy": f"{pair.system_accuracy:.3f}",
            "system_completeness": f"{pair.system_completeness:.3f}",
            "system_coverage": f"{pair.system_coverage:.3f}",
            "holistic_accuracy_delta_vs_system": f"{(holistic_accuracy - pair.system_accuracy):+.3f}",
            "holistic_coverage_delta_vs_system": f"{(holistic_coverage - pair.system_coverage):+.3f}",
            "accuracy_reason": accuracy_reason,
            "coverage_reason": coverage_reason,
            "candidate_path": str(paths["candidate_path"]),
            "gt_path": str(paths["gt_path"]),
            "report_path": pair.report_path,
            "note": f"deepeval_model={args.evaluation_model}",
        }
        output_rows.append(row)
        append_csv_row(args.output_csv, row)
        completed_pairs.add(key)

        logging.info(
            "[%d/%d] %s %s %s -> holistic_accuracy=%.3f holistic_coverage=%.3f",
            idx,
            len(pairs),
            pair.dataset_type,
            pair.meeting_id,
            pair.candidate_model,
            holistic_accuracy,
            holistic_coverage,
        )

    finalize_output_csv(args.output_csv, output_rows, aggregate, pair_lookup)
    logging.info("Wrote typed DeepEval comparison report to %s", args.output_csv)


if __name__ == "__main__":
    main()
