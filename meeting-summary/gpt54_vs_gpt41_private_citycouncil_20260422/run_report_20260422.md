# GPT-5.4 vs GPT-4.1 Focused Benchmark Run Report

This report documents the latest completed `gpt-5.4` versus `gpt-4.1` benchmark run over the `private_data` and `city_council` slices. It is intended as an operational companion to the paper's focused comparison results.

## Run Identity

- Run summary: [meeting_notes_model_comparison_run_standard_20260422_134801.json](/Users/lizhon/PycharmProjects/WebexSuiteAI/dataset-pipeline/report/private_citycouncil_model_comparison_gpt41_gpt54_20260422/full/meeting_notes_model_comparison_run_standard_20260422_134801.json)
- Offline-eval summary: [meeting_notes_model_comparison_offline_eval_standard_20260422_134801.json](/Users/lizhon/PycharmProjects/WebexSuiteAI/dataset-pipeline/report/private_citycouncil_model_comparison_gpt41_gpt54_20260422/full/meeting_notes_model_comparison_offline_eval_standard_20260422_134801.json)
- Combined report: [meeting_notes_model_comparison_combined_20260422_134801.csv](/Users/lizhon/PycharmProjects/WebexSuiteAI/dataset-pipeline/report/private_citycouncil_model_comparison_gpt41_gpt54_20260422/full/meeting_notes_model_comparison_combined_20260422_134801.csv)
- Significance report: [meeting_notes_model_comparison_gpt54_vs_gpt41_significance_20260422.csv](/Users/lizhon/PycharmProjects/WebexSuiteAI/dataset-pipeline/report/private_citycouncil_model_comparison_gpt41_gpt54_20260422/full/meeting_notes_model_comparison_gpt54_vs_gpt41_significance_20260422.csv)

## Scope

- Candidate models: `gpt-4.1`, `gpt-5.4`
- Dataset types: `private_data`, `city_council`
- Meetings: `56`
- Meeting-model tasks: `112`
- Evaluator runs: `224`
- Concurrency: `6`

## Runtime Window

- Summary creation timestamp (`generated_at`): `2026-04-22 13:48:01 +0800`
- Final run-summary write time: `2026-04-22 16:02:01 +0800`
- Observed elapsed wall-clock time for the final rerun: `2h 14m 00s`
- First newly completed task in this rerun: `2026-04-22 13:54:08 +0800`, `t_012 / gpt-4.1`
- Last newly completed task in this rerun: `2026-04-22 16:02:01 +0800`, `t_85889445716932507123321064915811827639 / gpt-5.4`

## Rerun Behavior

This latest run was not a zero-baseline execution. It was a rerun over the same output directory after an earlier partial run:

- Earlier partial run summary: [meeting_notes_model_comparison_run_standard_20260422_120039.json](/Users/lizhon/PycharmProjects/WebexSuiteAI/dataset-pipeline/report/private_citycouncil_model_comparison_gpt41_gpt54_20260422/full/meeting_notes_model_comparison_run_standard_20260422_120039.json)
- Earlier run launch time: `2026-04-22 12:00:39 +0800`
- Earlier run concurrency: `2`
- Earlier run partial progress: `20 completed`, `2 reused`, `0 failed`, `0 exceptions`

The final run intentionally increased concurrency from `2` to `6`, so the reported final wall-clock window should be interpreted as a higher-concurrency rerun with partial artifact reuse rather than as a single uninterrupted zero-baseline batch.

The final rerun inherited completed artifacts from that earlier attempt:

- Reused tasks in the final run: `21`
- Newly completed tasks in the final run: `91`
- Failed tasks: `0`
- Exception tasks: `0`

The reuse boundary is operationally clear:

- Fully reused meetings: `t_001` through `t_010` for both models
- Partially reused meeting: `t_011`, where `gpt-4.1` was reused and `gpt-5.4` was regenerated
- First newly completed `private_data` task: `t_012 / gpt-4.1`
- Last newly completed `private_data` task: `t_021 / gpt-5.4` at `2026-04-22 14:25:06 +0800`
- First newly completed `city_council` task: `t_10062873984778850834470432363897468907 / gpt-4.1` at `2026-04-22 14:27:05 +0800`

This means the final rerun spent approximately the first `37` minutes completing the remaining `private_data` work and the remaining `1h 35m` on the `city_council` slice.

## Completion Summary

| Scope | Completed | Reused | Failed | Exceptions |
|---|---:|---:|---:|---:|
| all tasks | 91 | 21 | 0 | 0 |
| `gpt-4.1` | 45 | 11 | 0 | 0 |
| `gpt-5.4` | 46 | 10 | 0 | 0 |

The offline-evaluation side also closed cleanly:

| Artifact summary | Value |
|---|---:|
| `task_count` | 112 |
| `reports_found` | 112 |
| `reports_missing` | 0 |
| `evaluator_run_count` | 224 |

## Result Summary

| Scope | Model | Meetings | Evaluator runs | Accuracy | Completeness | Coverage | Mean of 3 metrics |
|---|---|---:|---:|---:|---:|---:|---:|
| overall | `gpt-4.1` | 56 | 112 | 0.739 | 0.789 | 0.794 | 0.774 |
| overall | `gpt-5.4` | 56 | 112 | 0.754 | 0.844 | 0.868 | 0.822 |
| `city_council` | `gpt-4.1` | 34 | 68 | 0.745 | 0.781 | 0.781 | 0.769 |
| `city_council` | `gpt-5.4` | 34 | 68 | 0.760 | 0.830 | 0.834 | 0.808 |
| `private_data` | `gpt-4.1` | 22 | 44 | 0.729 | 0.801 | 0.816 | 0.782 |
| `private_data` | `gpt-5.4` | 22 | 44 | 0.745 | 0.865 | 0.920 | 0.843 |

## Meeting-Level Outcome Summary

| Dataset type | Metric | Meetings | `gpt-5.4` wins | `gpt-4.1` wins | Ties | Avg delta (`gpt-5.4 - gpt-4.1`) | Exact two-sided sign-test p |
|---|---|---:|---:|---:|---:|---:|---:|
| overall | accuracy | 56 | 30 | 24 | 2 | 0.015 | 0.496617 |
| overall | completeness | 56 | 52 | 3 | 1 | 0.055 | 1.54 × 10⁻¹² |
| overall | coverage | 56 | 41 | 8 | 7 | 0.074 | 1.96 × 10⁻⁶ |
| `city_council` | accuracy | 34 | 17 | 15 | 2 | 0.015 | 0.860050 |
| `city_council` | completeness | 34 | 31 | 2 | 1 | 0.049 | 1.31 × 10⁻⁷ |
| `city_council` | coverage | 34 | 22 | 5 | 7 | 0.054 | 0.001514 |
| `private_data` | accuracy | 22 | 13 | 9 | 0 | 0.016 | 0.523467 |
| `private_data` | completeness | 22 | 21 | 1 | 0 | 0.064 | 1.10 × 10⁻⁵ |
| `private_data` | coverage | 22 | 19 | 3 | 0 | 0.105 | 0.000855 |

## Operational Interpretation

Three operational points matter for the paper.

1. The run closed without missing reports, failed tasks, or exception tasks. This matters because the focused comparison is not based on a partially successful batch.
2. The final output is the result of a clean rerun strategy rather than a hand-merged artifact set. The reuse behavior is explicit in the run summary and confined to artifacts already completed in the earlier partial attempt.
3. The focused benchmark supports a deployment-facing recommendation because the result is simultaneously complete, statistically interpretable, and operationally reproducible from persisted artifacts.

## Paper Use

This run report is best cited as the operational provenance note for the focused `gpt-5.4` versus `gpt-4.1` comparison reported in `meeting-summary-system-paper_v24.md`.
