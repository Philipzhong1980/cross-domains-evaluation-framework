from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import median


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_DIR = PROJECT_ROOT / "report" / "logs"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "report"


METRIC_COMPLETION_RE = re.compile(
    r"(?P<metric>Generalmetric|Accuracymetric|Completenessmetric|Coveragemetric) "
    r"evaluation completed successfully - Model: (?P<model>[^,]+), "
    r"Total time: (?P<total>[0-9.]+) s \(LLM: (?P<llm>[0-9.]+) s, Parsing: (?P<parsing>[0-9.]+) s\), "
    r"Attempts: (?P<attempts>\d+)"
)

TOKENS_RE = re.compile(
    r"Prompt Tokens: (?P<prompt>\d+), Completion Tokens: (?P<completion>\d+), Total Tokens: (?P<total>\d+)"
)

OFFLINE_JOB_RE = re.compile(
    r"Offline evaluation completed - Total time: (?P<total>[0-9.]+) seconds, "
    r"Successful evaluations: (?P<success>\d+)/(?P<expected>\d+), "
    r"Average time per evaluation: (?P<avg>[0-9.]+) seconds"
)

METRIC_STAGE_MAP = {
    "Generalmetric": "general_evaluation",
    "Accuracymetric": "accuracy_evaluation",
    "Completenessmetric": "completeness_evaluation",
    "Coveragemetric": "coverage_evaluation",
}


@dataclass
class MetricRecord:
    stage: str
    evaluator_model: str
    total_seconds: float
    llm_seconds: float
    parsing_seconds: float
    attempts: int
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    source_file: str
    line_no: int


@dataclass
class OfflineEvalRecord:
    total_seconds: float
    successful_evaluations: int
    expected_evaluations: int
    average_time_per_evaluation_seconds: float
    source_file: str
    line_no: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export measured telemetry summaries from retained batch logs. "
            "This parser only reports stages that have explicit completion lines in the logs."
        )
    )
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def discover_log_files(log_dir: Path) -> list[Path]:
    patterns = [
        "batch_meeting_notes_model_comparison_*.log",
        "batch_meeting_notes_model_comparison_repair_*.log",
    ]
    files: list[Path] = []
    for pattern in patterns:
        files.extend(sorted(log_dir.glob(pattern)))
    return sorted(set(files))


def find_nearest_tokens(lines: list[str], index: int, lookback: int = 6) -> tuple[int | None, int | None, int | None]:
    for candidate_index in range(index - 1, max(-1, index - lookback - 1), -1):
        token_match = TOKENS_RE.search(lines[candidate_index])
        if token_match:
            return (
                int(token_match.group("prompt")),
                int(token_match.group("completion")),
                int(token_match.group("total")),
            )
    return None, None, None


def parse_logs(log_files: list[Path]) -> tuple[list[MetricRecord], list[OfflineEvalRecord]]:
    metric_records: list[MetricRecord] = []
    offline_records: list[OfflineEvalRecord] = []

    for log_file in log_files:
        lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        for idx, line in enumerate(lines):
            metric_match = METRIC_COMPLETION_RE.search(line)
            if metric_match:
                prompt_tokens, completion_tokens, total_tokens = find_nearest_tokens(lines, idx)
                metric_records.append(
                    MetricRecord(
                        stage=METRIC_STAGE_MAP[metric_match.group("metric")],
                        evaluator_model=metric_match.group("model"),
                        total_seconds=float(metric_match.group("total")),
                        llm_seconds=float(metric_match.group("llm")),
                        parsing_seconds=float(metric_match.group("parsing")),
                        attempts=int(metric_match.group("attempts")),
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        source_file=log_file.name,
                        line_no=idx + 1,
                    )
                )
                continue

            offline_match = OFFLINE_JOB_RE.search(line)
            if offline_match:
                offline_records.append(
                    OfflineEvalRecord(
                        total_seconds=float(offline_match.group("total")),
                        successful_evaluations=int(offline_match.group("success")),
                        expected_evaluations=int(offline_match.group("expected")),
                        average_time_per_evaluation_seconds=float(offline_match.group("avg")),
                        source_file=log_file.name,
                        line_no=idx + 1,
                    )
                )
    return metric_records, offline_records


def safe_mean(values: list[float | int | None]) -> float | None:
    filtered = [float(v) for v in values if v is not None]
    if not filtered:
        return None
    return sum(filtered) / len(filtered)


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * pct
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def build_metric_summary_rows(metric_records: list[MetricRecord]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    stages = sorted({record.stage for record in metric_records})
    for stage in stages:
        stage_records = [record for record in metric_records if record.stage == stage]
        total_values = [record.total_seconds for record in stage_records]
        llm_values = [record.llm_seconds for record in stage_records]
        parsing_values = [record.parsing_seconds for record in stage_records]
        rows.append(
            {
                "row_type": "metric_stage_summary",
                "stage": stage,
                "sample_count": str(len(stage_records)),
                "avg_total_seconds": f"{safe_mean(total_values):.2f}",
                "median_total_seconds": f"{median(total_values):.2f}",
                "p90_total_seconds": f"{percentile(total_values, 0.90):.2f}",
                "avg_llm_seconds": f"{safe_mean(llm_values):.2f}",
                "avg_parsing_seconds": f"{safe_mean(parsing_values):.2f}",
                "avg_prompt_tokens": f"{safe_mean([record.prompt_tokens for record in stage_records]) or 0:.2f}",
                "avg_completion_tokens": f"{safe_mean([record.completion_tokens for record in stage_records]) or 0:.2f}",
                "avg_total_tokens": f"{safe_mean([record.total_tokens for record in stage_records]) or 0:.2f}",
                "notes": "Explicit evaluator completion lines with nearest preceding token log.",
            }
        )
    return rows


def build_metric_model_rows(metric_records: list[MetricRecord]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    keys = sorted({(record.stage, record.evaluator_model) for record in metric_records})
    for stage, evaluator_model in keys:
        subset = [
            record for record in metric_records
            if record.stage == stage and record.evaluator_model == evaluator_model
        ]
        if not subset:
            continue
        total_values = [record.total_seconds for record in subset]
        rows.append(
            {
                "row_type": "metric_stage_model_summary",
                "stage": stage,
                "evaluator_model": evaluator_model,
                "sample_count": str(len(subset)),
                "avg_total_seconds": f"{safe_mean(total_values):.2f}",
                "median_total_seconds": f"{median(total_values):.2f}",
                "p90_total_seconds": f"{percentile(total_values, 0.90):.2f}",
                "avg_llm_seconds": f"{safe_mean([record.llm_seconds for record in subset]):.2f}",
                "avg_prompt_tokens": f"{safe_mean([record.prompt_tokens for record in subset]) or 0:.2f}",
                "avg_completion_tokens": f"{safe_mean([record.completion_tokens for record in subset]) or 0:.2f}",
                "avg_total_tokens": f"{safe_mean([record.total_tokens for record in subset]) or 0:.2f}",
                "notes": "Grouped by evaluator model from explicit completion lines.",
            }
        )
    return rows


def build_offline_summary_rows(offline_records: list[OfflineEvalRecord]) -> list[dict[str, str]]:
    if not offline_records:
        return []
    total_values = [record.total_seconds for record in offline_records]
    avg_eval_values = [record.average_time_per_evaluation_seconds for record in offline_records]
    return [
        {
            "row_type": "offline_eval_job_summary",
            "stage": "offline_evaluation_job",
            "sample_count": str(len(offline_records)),
            "avg_total_seconds": f"{safe_mean(total_values):.2f}",
            "median_total_seconds": f"{median(total_values):.2f}",
            "p90_total_seconds": f"{percentile(total_values, 0.90):.2f}",
            "avg_time_per_evaluation_seconds": f"{safe_mean(avg_eval_values):.2f}",
            "avg_successful_evaluations_per_job": f"{safe_mean([record.successful_evaluations for record in offline_records]):.2f}",
            "notes": "Explicit offline evaluation completion lines.",
        }
    ]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    args = parse_args()
    log_files = discover_log_files(args.log_dir)
    metric_records, offline_records = parse_logs(log_files)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_rows = (
        build_metric_summary_rows(metric_records)
        + build_metric_model_rows(metric_records)
        + build_offline_summary_rows(offline_records)
    )
    summary_csv = args.output_dir / f"measured_stage_level_telemetry_from_logs_{timestamp}.csv"
    detail_csv = args.output_dir / f"measured_stage_level_telemetry_from_logs_detail_{timestamp}.csv"

    write_csv(summary_csv, summary_rows)

    detail_rows: list[dict[str, str]] = []
    for record in metric_records:
        detail_rows.append(
            {
                "row_type": "metric_call",
                "stage": record.stage,
                "evaluator_model": record.evaluator_model,
                "total_seconds": f"{record.total_seconds:.2f}",
                "llm_seconds": f"{record.llm_seconds:.2f}",
                "parsing_seconds": f"{record.parsing_seconds:.2f}",
                "attempts": str(record.attempts),
                "prompt_tokens": "" if record.prompt_tokens is None else str(record.prompt_tokens),
                "completion_tokens": "" if record.completion_tokens is None else str(record.completion_tokens),
                "total_tokens": "" if record.total_tokens is None else str(record.total_tokens),
                "source_file": record.source_file,
                "line_no": str(record.line_no),
            }
        )
    for record in offline_records:
        detail_rows.append(
            {
                "row_type": "offline_eval_job",
                "stage": "offline_evaluation_job",
                "total_seconds": f"{record.total_seconds:.2f}",
                "successful_evaluations": str(record.successful_evaluations),
                "expected_evaluations": str(record.expected_evaluations),
                "avg_time_per_evaluation_seconds": f"{record.average_time_per_evaluation_seconds:.2f}",
                "source_file": record.source_file,
                "line_no": str(record.line_no),
            }
        )
    write_csv(detail_csv, detail_rows)

    print(summary_csv)
    print(detail_csv)
    print(f"metric_records={len(metric_records)} offline_eval_jobs={len(offline_records)} log_files={len(log_files)}")


if __name__ == "__main__":
    main()
