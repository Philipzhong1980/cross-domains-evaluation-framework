from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from io import StringIO
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from generator.meetingnotes_candidate import MeetingNotesCandidate  # noqa: E402
from generator.meetingsummary_dataset import Meeting, MeetingDataset, MeetingType  # noqa: E402
from log_config import get_logger, setup_logging  # noqa: E402
from prompts.common.prompt_registry import PromptRegistry  # noqa: E402
from service.offline_evaluation_service import OfflineEvaluationService  # noqa: E402
from util.file_manager import FileManager  # noqa: E402


DEFAULT_DATASET_ROOT = PROJECT_ROOT / "dataset"
DEFAULT_CANDIDATE_VARIANT = "standard"
DEFAULT_CANDIDATE_VERSION = "baseline.md"
DEFAULT_CONCURRENCY = 4
MODEL_ALIASES = {
    "gpt-4.1-mini": "gpt-4.1-mini",
    "gpt-5-mini": "gpt-5-mini-2025-08-07",
    "gpt-5.1": "gpt-5.1",
}
RUN_REPORT_FIELDS = [
    "meeting_id",
    "candidate_model",
    "candidate_model_slug",
    "candidate_variant",
    "candidate_version",
    "report_variant",
    "status",
    "candidate_path",
    "report_path",
    "error",
]
OFFLINE_EVAL_REPORT_FIELDS = [
    "meeting_id",
    "candidate_model",
    "candidate_model_slug",
    "report_variant",
    "status",
    "report_exists",
    "evaluator_run_count",
    "accuracy_avg",
    "completeness_avg",
    "coverage_avg",
    "quality_avg",
    "report_path",
    "error",
]

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Batch-generate meeting-note candidates for multiple models and run "
            "offline evaluation against the existing GT without overwriting prior results."
        )
    )
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--meeting-id", action="append", dest="meeting_ids")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--candidate-variant", default=DEFAULT_CANDIDATE_VARIANT)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--summary-output-dir", type=Path)
    return parser.parse_args()


def model_slug(model: str) -> str:
    streamlined = Meeting._streamline_model_name(model)
    if streamlined:
        return streamlined
    return model


def build_report_variant(candidate_variant: str, candidate_model: str) -> str:
    return f"{candidate_variant}_{model_slug(candidate_model)}"


def default_summary_output_dir() -> Path:
    return PROJECT_ROOT / "report"


def build_report_base_name(report_kind: str, candidate_variant: str, run_timestamp: str) -> str:
    return f"meeting_notes_model_comparison_{report_kind}_{candidate_variant}_{run_timestamp}"


def build_artifact_paths(
    meeting: Meeting,
    candidate_variant: str,
    candidate_model: str,
    candidate_version: str,
    report_variant: str,
) -> tuple[Path, Path]:
    candidate_path = meeting.candidate_path(
        variant=candidate_variant,
        model=candidate_model,
        filename=candidate_version,
    )
    report_path = meeting.evaluation_base_path(
        eval_type="offline",
        variant=report_variant,
    )
    return candidate_path, report_path


def write_summary_artifacts(
    output_dir: Path,
    base_name: str,
    payload: dict,
    rows: list[dict[str, str]],
    fieldnames: list[str],
) -> tuple[Path, Path]:
    json_path = output_dir / f"{base_name}.json"
    csv_path = output_dir / f"{base_name}.csv"

    FileManager.ensure_parent(json_path)
    FileManager.ensure_parent(csv_path)
    FileManager.write_json(json_path, payload)

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in fieldnames})
    FileManager.write_text(csv_path, buffer.getvalue())

    return json_path, csv_path


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def offline_report_is_complete(report_path: Path) -> tuple[bool, str]:
    if not report_path.exists():
        return False, "missing"

    try:
        report_json = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return False, "invalid_json"

    if not isinstance(report_json, dict) or len(report_json) < 2:
        return False, "missing_evaluators"

    required_scores = ("accuracy_score", "completeness_score", "coverage_score")
    for evaluator_entry in report_json.values():
        if not isinstance(evaluator_entry, dict):
            return False, "invalid_entry"
        for score_key in required_scores:
            if evaluator_entry.get(score_key) is None:
                return False, f"missing_{score_key}"

    return True, ""


def archive_incomplete_report(report_path: Path) -> Path | None:
    if not report_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archived_path = report_path.with_name(f"{report_path.stem}.incomplete_{timestamp}{report_path.suffix}")
    report_path.rename(archived_path)
    return archived_path


def build_offline_eval_payload(
    metadata: dict,
    task_rows: list[dict[str, str]],
    run_status: str,
) -> tuple[dict, list[dict[str, str]]]:
    metric_keys = [
        "accuracy_score",
        "completeness_score",
        "coverage_score",
        "readability_score",
        "fluency_score",
        "coherence_score",
        "tone_score",
    ]
    quality_keys = ["accuracy_score", "completeness_score", "coverage_score"]

    evaluator_rows: list[dict[str, str | float | int | None]] = []
    task_summary_rows: list[dict[str, str | float | int | None]] = []
    model_metric_values: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    evaluator_metric_values: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    reports_found = 0
    reports_missing = 0

    for task in task_rows:
        report_path_text = task.get("report_path", "")
        report_path = Path(report_path_text) if report_path_text else None
        if not report_path or not report_path.exists():
            reports_missing += 1
            task_summary_rows.append(
                {
                    "meeting_id": task.get("meeting_id", ""),
                    "candidate_model": task.get("candidate_model", ""),
                    "candidate_model_slug": task.get("candidate_model_slug", ""),
                    "report_variant": task.get("report_variant", ""),
                    "status": task.get("status", ""),
                    "report_path": report_path_text,
                    "report_exists": False,
                    "evaluator_run_count": 0,
                    "accuracy_avg": None,
                    "completeness_avg": None,
                    "coverage_avg": None,
                    "quality_avg": None,
                    "error": task.get("error", ""),
                }
            )
            continue

        reports_found += 1
        report_json = json.loads(report_path.read_text(encoding="utf-8"))
        task_metric_values: dict[str, list[float]] = defaultdict(list)

        for evaluator_entry in report_json.values():
            evaluator_model = evaluator_entry.get("evaluator_model", "")
            evaluator_row = {
                "meeting_id": evaluator_entry.get("meeting_id", task.get("meeting_id", "")),
                "candidate_model": evaluator_entry.get("candidate_model", task.get("candidate_model", "")),
                "candidate_model_slug": task.get("candidate_model_slug", ""),
                "evaluator_model": evaluator_model,
                "accuracy_score": evaluator_entry.get("accuracy_score"),
                "completeness_score": evaluator_entry.get("completeness_score"),
                "coverage_score": evaluator_entry.get("coverage_score"),
                "quality_score": _mean(
                    [
                        score
                        for score in [
                            evaluator_entry.get("accuracy_score"),
                            evaluator_entry.get("completeness_score"),
                            evaluator_entry.get("coverage_score"),
                        ]
                        if isinstance(score, (int, float))
                    ]
                ),
                "readability_score": evaluator_entry.get("readability_score"),
                "fluency_score": evaluator_entry.get("fluency_score"),
                "coherence_score": evaluator_entry.get("coherence_score"),
                "tone_score": evaluator_entry.get("tone_score"),
                "report_path": str(report_path),
            }
            evaluator_rows.append(evaluator_row)

            for metric_key in metric_keys:
                metric_value = evaluator_entry.get(metric_key)
                if isinstance(metric_value, (int, float)):
                    task_metric_values[metric_key].append(float(metric_value))
                    model_metric_values[task.get("candidate_model_slug", "")][metric_key].append(float(metric_value))
                    evaluator_metric_values[evaluator_model][metric_key].append(float(metric_value))

        task_quality_values: list[float] = []
        for metric_key in quality_keys:
            task_quality_values.extend(task_metric_values.get(metric_key, []))

        task_summary_rows.append(
            {
                "meeting_id": task.get("meeting_id", ""),
                "candidate_model": task.get("candidate_model", ""),
                "candidate_model_slug": task.get("candidate_model_slug", ""),
                "report_variant": task.get("report_variant", ""),
                "status": task.get("status", ""),
                "report_path": str(report_path),
                "report_exists": True,
                "evaluator_run_count": len(report_json),
                "accuracy_avg": _mean(task_metric_values.get("accuracy_score", [])),
                "completeness_avg": _mean(task_metric_values.get("completeness_score", [])),
                "coverage_avg": _mean(task_metric_values.get("coverage_score", [])),
                "quality_avg": _mean(task_quality_values),
                "error": task.get("error", ""),
            }
        )

    candidate_model_summary: dict[str, dict[str, float | int | None]] = {}
    for candidate_model_slug, metric_map in model_metric_values.items():
        metric_summary = {
            metric_key: _mean(values)
            for metric_key, values in metric_map.items()
        }
        quality_values: list[float] = []
        for metric_key in quality_keys:
            quality_values.extend(metric_map.get(metric_key, []))
        candidate_model_summary[candidate_model_slug] = {
            "evaluator_run_count": len(
                [row for row in evaluator_rows if row["candidate_model_slug"] == candidate_model_slug]
            ),
            "meeting_count": len(
                {row["meeting_id"] for row in task_summary_rows if row["candidate_model_slug"] == candidate_model_slug and row["report_exists"]}
            ),
            "accuracy_avg": metric_summary.get("accuracy_score"),
            "completeness_avg": metric_summary.get("completeness_score"),
            "coverage_avg": metric_summary.get("coverage_score"),
            "quality_avg": _mean(quality_values),
            "readability_avg": metric_summary.get("readability_score"),
            "fluency_avg": metric_summary.get("fluency_score"),
            "coherence_avg": metric_summary.get("coherence_score"),
            "tone_avg": metric_summary.get("tone_score"),
        }

    evaluator_model_summary: dict[str, dict[str, float | int | None]] = {}
    for evaluator_model, metric_map in evaluator_metric_values.items():
        metric_summary = {
            metric_key: _mean(values)
            for metric_key, values in metric_map.items()
        }
        quality_values: list[float] = []
        for metric_key in quality_keys:
            quality_values.extend(metric_map.get(metric_key, []))
        evaluator_model_summary[evaluator_model] = {
            "evaluator_run_count": len([row for row in evaluator_rows if row["evaluator_model"] == evaluator_model]),
            "accuracy_avg": metric_summary.get("accuracy_score"),
            "completeness_avg": metric_summary.get("completeness_score"),
            "coverage_avg": metric_summary.get("coverage_score"),
            "quality_avg": _mean(quality_values),
            "readability_avg": metric_summary.get("readability_score"),
            "fluency_avg": metric_summary.get("fluency_score"),
            "coherence_avg": metric_summary.get("coherence_score"),
            "tone_avg": metric_summary.get("tone_score"),
        }

    payload = {
        "metadata": {
            **metadata,
            "run_status": run_status,
        },
        "summary": {
            "task_count": len(task_rows),
            "reports_found": reports_found,
            "reports_missing": reports_missing,
            "evaluator_run_count": len(evaluator_rows),
        },
        "candidate_model_summary": candidate_model_summary,
        "evaluator_model_summary": evaluator_model_summary,
        "task_summaries": task_summary_rows,
        "evaluator_runs": evaluator_rows,
    }

    csv_rows: list[dict[str, str]] = []
    for row in task_summary_rows:
        csv_rows.append(
            {
                "meeting_id": str(row.get("meeting_id", "")),
                "candidate_model": str(row.get("candidate_model", "")),
                "candidate_model_slug": str(row.get("candidate_model_slug", "")),
                "report_variant": str(row.get("report_variant", "")),
                "status": str(row.get("status", "")),
                "report_exists": str(row.get("report_exists", "")),
                "evaluator_run_count": str(row.get("evaluator_run_count", "")),
                "accuracy_avg": str(row.get("accuracy_avg", "")),
                "completeness_avg": str(row.get("completeness_avg", "")),
                "coverage_avg": str(row.get("coverage_avg", "")),
                "quality_avg": str(row.get("quality_avg", "")),
                "report_path": str(row.get("report_path", "")),
                "error": str(row.get("error", "")),
            }
        )

    return payload, csv_rows


def build_run_payload(
    metadata: dict,
    summary: dict[str, int],
    model_summary: dict[str, dict[str, int]],
    task_rows: list[dict[str, str]],
    run_status: str,
) -> dict:
    return {
        "metadata": {
            **metadata,
            "run_status": run_status,
        },
        "summary": summary,
        "model_summary": model_summary,
        "tasks": task_rows,
    }


def discover_meeting_ids(dataset_root: Path) -> list[str]:
    gt_root = dataset_root / "views" / "meeting_notes" / "ground_truth" / "internal"
    transcript_root = dataset_root / "assets" / "transcripts" / "internal"
    meeting_ids: list[str] = []

    for gt_path in sorted(gt_root.glob("*/meetingsummary/ground_truth.json")):
        meeting_id = gt_path.parent.parent.name
        transcript_path = transcript_root / meeting_id / "original_transcript.txt"
        if transcript_path.exists():
            meeting_ids.append(meeting_id)

    return meeting_ids


async def process_meeting_model(
    dataset_root: Path,
    meeting_id: str,
    candidate_variant: str,
    candidate_model: str,
    semaphore: asyncio.Semaphore,
) -> dict[str, str]:
    async with semaphore:
        dataset = MeetingDataset(dataset_root)
        meeting = dataset.meeting(MeetingType.INTERNAL, meeting_id)
        candidate_version = DEFAULT_CANDIDATE_VERSION
        report_variant = build_report_variant(candidate_variant, candidate_model)
        candidate_path, report_path = build_artifact_paths(
            meeting=meeting,
            candidate_variant=candidate_variant,
            candidate_model=candidate_model,
            candidate_version=candidate_version,
            report_variant=report_variant,
        )

        if not meeting.transcript_exists() or not meeting.ground_truth_exists("meetingsummary"):
            logger.error(
                "model_comparison_missing_inputs",
                extra={
                    "meeting_id": meeting_id,
                    "candidate_model": candidate_model,
                    "transcript_exists": meeting.transcript_exists(),
                    "ground_truth_exists": meeting.ground_truth_exists("meetingsummary"),
                },
            )
            return {
                "meeting_id": meeting_id,
                "candidate_model": candidate_model,
                "candidate_model_slug": model_slug(candidate_model),
                "candidate_variant": candidate_variant,
                "candidate_version": candidate_version,
                "report_variant": report_variant,
                "candidate_path": str(candidate_path),
                "report_path": str(report_path),
                "error": "missing_inputs",
                "status": "failed",
            }

        transcript_text = meeting.load_transcript()
        gt_text = meeting.load_ground_truth("meetingsummary")
        gt_json = json.loads(gt_text)
        candidate_existed = candidate_path.exists()
        report_complete, report_issue = offline_report_is_complete(report_path)

        logger.info(
            "model_comparison_task_started",
            extra={
                "meeting_id": meeting_id,
                "candidate_variant": candidate_variant,
                "candidate_model": candidate_model,
                "candidate_version": candidate_version,
                "report_variant": report_variant,
                "transcript_chars": len(transcript_text),
                "gt_topic_count": len(gt_json.get("topics", [])),
                "gt_decision_count": len(gt_json.get("decisions", [])),
            },
        )

        if candidate_existed and report_complete:
            logger.info(
                "model_comparison_task_skipped_existing",
                extra={
                    "meeting_id": meeting_id,
                    "candidate_model": candidate_model,
                    "candidate_path": str(candidate_path),
                    "report_path": str(report_path),
                },
            )
            return {
                "meeting_id": meeting_id,
                "candidate_model": candidate_model,
                "candidate_model_slug": model_slug(candidate_model),
                "candidate_variant": candidate_variant,
                "candidate_version": candidate_version,
                "report_variant": report_variant,
                "candidate_path": str(candidate_path),
                "report_path": str(report_path),
                "error": "",
                "status": "reused",
            }

        if not candidate_existed:
            generator = MeetingNotesCandidate(prompt_registry=PromptRegistry())
            await generator.generate_candidates(
                meeting=meeting,
                candidate_variant=candidate_variant,
                model=candidate_model,
                filename=candidate_version,
            )
        elif not report_complete:
            archived_report_path = archive_incomplete_report(report_path)
            logger.info(
                "model_comparison_rerun_eval_for_incomplete_report",
                extra={
                    "meeting_id": meeting_id,
                    "candidate_model": candidate_model,
                    "report_path": str(report_path),
                    "report_issue": report_issue,
                    "archived_report_path": str(archived_report_path) if archived_report_path else "",
                },
            )

        eval_service = OfflineEvaluationService()
        eval_result = await eval_service.evaluate(
            meeting_id=meeting_id,
            summary_style=candidate_variant,
            candidate_variant=candidate_variant,
            report_variant=report_variant,
            candidate_model=candidate_model,
            candidate_version=candidate_version,
        )

        if not eval_result.ok:
            logger.error(
                "model_comparison_task_failed",
                extra={
                    "meeting_id": meeting_id,
                    "candidate_model": candidate_model,
                    "candidate_version": candidate_version,
                    "report_variant": report_variant,
                    "error": eval_result.error,
                },
            )
            return {
                "meeting_id": meeting_id,
                "candidate_model": candidate_model,
                "candidate_model_slug": model_slug(candidate_model),
                "candidate_variant": candidate_variant,
                "candidate_version": candidate_version,
                "report_variant": report_variant,
                "candidate_path": str(candidate_path),
                "report_path": str(report_path),
                "error": json.dumps(eval_result.error, ensure_ascii=False) if eval_result.error else "",
                "status": "failed",
            }

        logger.info(
            "model_comparison_task_finished",
            extra={
                "meeting_id": meeting_id,
                "candidate_model": candidate_model,
                "candidate_path": str(candidate_path),
                "report_path": str(report_path),
                "status": "completed",
            },
        )
        return {
            "meeting_id": meeting_id,
            "candidate_model": candidate_model,
            "candidate_model_slug": model_slug(candidate_model),
            "candidate_variant": candidate_variant,
            "candidate_version": candidate_version,
            "report_variant": report_variant,
            "candidate_path": str(candidate_path),
            "report_path": str(report_path),
            "error": "",
            "status": "completed",
        }


async def process_meeting_model_safe(
    dataset_root: Path,
    meeting_id: str,
    candidate_variant: str,
    candidate_model: str,
    semaphore: asyncio.Semaphore,
) -> dict[str, str]:
    try:
        return await process_meeting_model(
            dataset_root=dataset_root,
            meeting_id=meeting_id,
            candidate_variant=candidate_variant,
            candidate_model=candidate_model,
            semaphore=semaphore,
        )
    except Exception as exc:
        logger.error(
            "model_comparison_task_exception",
            exc_info=(type(exc), exc, exc.__traceback__),
            extra={
                "meeting_id": meeting_id,
                "candidate_model": candidate_model,
            },
        )
        return {
            "meeting_id": meeting_id,
            "candidate_model": candidate_model,
            "candidate_model_slug": model_slug(candidate_model),
            "candidate_variant": candidate_variant,
            "candidate_version": DEFAULT_CANDIDATE_VERSION,
            "report_variant": build_report_variant(candidate_variant, candidate_model),
            "status": "exception",
            "candidate_path": "",
            "report_path": "",
            "error": str(exc),
        }


async def main() -> None:
    args = parse_args()
    setup_logging()
    summary_output_dir = args.summary_output_dir or default_summary_output_dir()
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    meeting_ids = args.meeting_ids or discover_meeting_ids(args.dataset_root)
    if args.limit is not None:
        meeting_ids = meeting_ids[: args.limit]

    tasks_to_run: list[tuple[str, str]] = []
    for meeting_id in meeting_ids:
        for candidate_model in MODEL_ALIASES.values():
            tasks_to_run.append((meeting_id, candidate_model))

    logger.info(
        "model_comparison_batch_started",
        extra={
            "dataset_root": str(args.dataset_root),
            "meeting_count": len(meeting_ids),
            "task_count": len(tasks_to_run),
            "candidate_variant": args.candidate_variant,
            "candidate_version": DEFAULT_CANDIDATE_VERSION,
            "candidate_models": list(MODEL_ALIASES.values()),
            "concurrency": args.concurrency,
            "summary_output_dir": str(summary_output_dir),
        },
    )

    shared_metadata = {
        "dataset_root": str(args.dataset_root),
        "summary_output_dir": str(summary_output_dir),
        "candidate_variant": args.candidate_variant,
        "candidate_version": DEFAULT_CANDIDATE_VERSION,
        "candidate_models": list(MODEL_ALIASES.values()),
        "meeting_ids": meeting_ids,
        "concurrency": args.concurrency,
        "task_count": len(tasks_to_run),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }

    run_report_base_name = build_report_base_name("run", args.candidate_variant, run_timestamp)
    offline_eval_report_base_name = build_report_base_name("offline_eval", args.candidate_variant, run_timestamp)

    run_summary = {"completed": 0, "reused": 0, "failed": 0, "exceptions": 0}
    run_model_summary = {
        model_slug(model): {"completed": 0, "reused": 0, "failed": 0, "exceptions": 0}
        for model in MODEL_ALIASES.values()
    }
    initial_run_payload = build_run_payload(
        metadata=shared_metadata,
        summary=run_summary,
        model_summary=run_model_summary,
        task_rows=[],
        run_status="running",
    )
    run_summary_json_path, run_summary_csv_path = write_summary_artifacts(
        output_dir=summary_output_dir,
        base_name=run_report_base_name,
        payload=initial_run_payload,
        rows=[],
        fieldnames=RUN_REPORT_FIELDS,
    )
    initial_offline_payload, initial_offline_rows = build_offline_eval_payload(
        metadata=shared_metadata,
        task_rows=[],
        run_status="running",
    )
    offline_eval_json_path, offline_eval_csv_path = write_summary_artifacts(
        output_dir=summary_output_dir,
        base_name=offline_eval_report_base_name,
        payload=initial_offline_payload,
        rows=initial_offline_rows,
        fieldnames=OFFLINE_EVAL_REPORT_FIELDS,
    )

    semaphore = asyncio.Semaphore(args.concurrency)
    tasks = [
        asyncio.create_task(
            process_meeting_model_safe(
                dataset_root=args.dataset_root,
                meeting_id=meeting_id,
                candidate_variant=args.candidate_variant,
                candidate_model=candidate_model,
                semaphore=semaphore,
            )
        )
        for meeting_id, candidate_model in tasks_to_run
    ]

    summary = {"completed": 0, "reused": 0, "failed": 0, "exceptions": 0}
    model_summary = {
        model_slug(model): {"completed": 0, "reused": 0, "failed": 0, "exceptions": 0}
        for model in MODEL_ALIASES.values()
    }

    task_rows: list[dict[str, str]] = []
    for completed_task in asyncio.as_completed(tasks):
        result = await completed_task
        task_rows.append(result)
        status_key = "exceptions" if result["status"] == "exception" else result["status"]
        summary[status_key] += 1
        model_key = model_slug(result["candidate_model"])
        if model_key not in model_summary:
            model_summary[model_key] = {"completed": 0, "reused": 0, "failed": 0, "exceptions": 0}
        model_summary[model_key][status_key] += 1
        summary_payload = build_run_payload(
            metadata=shared_metadata,
            summary=summary,
            model_summary=model_summary,
            task_rows=task_rows,
            run_status="running",
        )
        run_summary_json_path, run_summary_csv_path = write_summary_artifacts(
            output_dir=summary_output_dir,
            base_name=run_report_base_name,
            payload=summary_payload,
            rows=task_rows,
            fieldnames=RUN_REPORT_FIELDS,
        )
        offline_eval_payload, offline_eval_rows = build_offline_eval_payload(
            metadata=shared_metadata,
            task_rows=task_rows,
            run_status="running",
        )
        offline_eval_json_path, offline_eval_csv_path = write_summary_artifacts(
            output_dir=summary_output_dir,
            base_name=offline_eval_report_base_name,
            payload=offline_eval_payload,
            rows=offline_eval_rows,
            fieldnames=OFFLINE_EVAL_REPORT_FIELDS,
        )

    summary_payload = build_run_payload(
        metadata=shared_metadata,
        summary=summary,
        model_summary=model_summary,
        task_rows=task_rows,
        run_status="completed",
    )
    run_summary_json_path, run_summary_csv_path = write_summary_artifacts(
        output_dir=summary_output_dir,
        base_name=run_report_base_name,
        payload=summary_payload,
        rows=task_rows,
        fieldnames=RUN_REPORT_FIELDS,
    )
    offline_eval_payload, offline_eval_rows = build_offline_eval_payload(
        metadata=shared_metadata,
        task_rows=task_rows,
        run_status="completed",
    )
    offline_eval_json_path, offline_eval_csv_path = write_summary_artifacts(
        output_dir=summary_output_dir,
        base_name=offline_eval_report_base_name,
        payload=offline_eval_payload,
        rows=offline_eval_rows,
        fieldnames=OFFLINE_EVAL_REPORT_FIELDS,
    )

    logger.info(
        "model_comparison_batch_finished",
        extra={
            "summary": summary,
            "model_summary": model_summary,
            "run_summary_json_path": str(run_summary_json_path),
            "run_summary_csv_path": str(run_summary_csv_path),
            "offline_eval_json_path": str(offline_eval_json_path),
            "offline_eval_csv_path": str(offline_eval_csv_path),
        },
    )


if __name__ == "__main__":
    asyncio.run(main())
