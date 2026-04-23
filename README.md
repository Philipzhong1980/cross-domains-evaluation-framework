# Cross-Domain Evaluation Framework

This repository is best understood as a public artifact package for the AI meeting-summary system paper, not as the complete internal production repository.

If you are opening the repo for the first time, the main entry points are under [`meeting-summary/`](meeting-summary):

- Latest paper source: [`meeting-summary/meeting-summary-system-paper_v24.md`](meeting-summary/meeting-summary-system-paper_v24.md)
- Paper PDF: [`meeting-summary/meeting-summary-system-paper_v24.pdf`](meeting-summary/meeting-summary-system-paper_v24.pdf)
- Main benchmark report: [`meeting-summary/meeting_notes_model_comparison_combined_20260417.csv`](meeting-summary/meeting_notes_model_comparison_combined_20260417.csv)
- Significance analysis: [`meeting-summary/meeting_notes_model_comparison_combined_significance_20260417.csv`](meeting-summary/meeting_notes_model_comparison_combined_significance_20260417.csv)
- `gpt-5.4` vs `gpt-4.1` follow-up bundle: [`meeting-summary/gpt54_vs_gpt41_private_citycouncil_20260422/README.md`](meeting-summary/gpt54_vs_gpt41_private_citycouncil_20260422/README.md)

## What Is In This Repo

```text
.
├── meeting-summary/
│   ├── meeting-summary-system-paper_v24.md/.html/.pdf
│   ├── meeting_notes_model_comparison_combined_20260417.csv
│   ├── meeting_notes_model_comparison_combined_significance_20260417.csv
│   ├── deepeval_typed_empirical_comparison_all_20260421.csv
│   ├── gt_agreement_stats_all_20260421.csv
│   ├── single_vs_two_judge_ablation_all_20260421.csv
│   ├── measured_stage_level_telemetry_from_logs_20260421_131115.csv
│   ├── batch_meeting_notes_model_comparison.py
│   ├── deepeval_typed_empirical_comparison.py
│   ├── export_measured_telemetry_from_logs.py
│   ├── gpt54_vs_gpt41_private_citycouncil_20260422/
│   └── dataset/
│       ├── assets/transcripts/internal/<meeting_id>/original_transcript.txt
│       └── views/meeting_notes/{ground_truth,candidate,evaluation}/...
└── LICENSE
```

You can think of the package as four layers:

1. `paper`: the manuscript in Markdown, PDF, and HTML, plus figures.
2. `benchmark reports`: the CSV and Markdown artifacts behind the paper’s core tables.
3. `public data package`: public transcript, GT, candidate, and evaluation artifacts.
4. `helper scripts`: a small set of export and comparison scripts used to inspect the reported results.

## Recommended Reading Order

### 1. Read the paper first

- Markdown is the best format if you want to cross-check claims against the repo: [`meeting-summary/meeting-summary-system-paper_v24.md`](meeting-summary/meeting-summary-system-paper_v24.md)
- Use the PDF if you just want the formatted paper: [`meeting-summary/meeting-summary-system-paper_v24.pdf`](meeting-summary/meeting-summary-system-paper_v24.pdf)

### 2. Then inspect the artifacts behind the main results

| Paper content | Artifact |
|---|---|
| Main benchmark (`114` meetings / `340` pairs / `680` judge runs) | [`meeting-summary/meeting_notes_model_comparison_combined_20260417.csv`](meeting-summary/meeting_notes_model_comparison_combined_20260417.csv) |
| Significance and pairwise sign tests | [`meeting-summary/meeting_notes_model_comparison_combined_significance_20260417.csv`](meeting-summary/meeting_notes_model_comparison_combined_significance_20260417.csv) |
| DeepEval baseline | [`meeting-summary/deepeval_typed_empirical_comparison_all_20260421.csv`](meeting-summary/deepeval_typed_empirical_comparison_all_20260421.csv) |
| GT agreement and temp-artifact retention notes | [`meeting-summary/gt_agreement_stats_all_20260421.csv`](meeting-summary/gt_agreement_stats_all_20260421.csv) |
| Single-judge vs two-judge ablation | [`meeting-summary/single_vs_two_judge_ablation_all_20260421.csv`](meeting-summary/single_vs_two_judge_ablation_all_20260421.csv) |
| Telemetry recovered from retained logs | [`meeting-summary/measured_stage_level_telemetry_from_logs_20260421_131115.csv`](meeting-summary/measured_stage_level_telemetry_from_logs_20260421_131115.csv) |

### 3. Finally read the follow-up bundle

If you want the deployment-oriented follow-up added after the main benchmark, namely `gpt-5.4` vs `gpt-4.1` on `private_data + city_council`, start here:

- [`meeting-summary/gpt54_vs_gpt41_private_citycouncil_20260422/README.md`](meeting-summary/gpt54_vs_gpt41_private_citycouncil_20260422/README.md)

That subdirectory is already organized in a practical order: top-line summary, per-slice tables, significance, analysis note, and run report. It is a derived report bundle only; it does not publish the `22` `private_data` meetings as raw artifacts, and it does not add any `private_data` files under `meeting-summary/dataset/`.

## Data Boundary and Reproducibility Boundary

This distinction matters, because it is easy to confuse the benchmark universe described in the paper with the raw artifacts packaged in this repo.

- The paper’s main benchmark contains `114` meetings.
- The dataset split is `34 city_council + 22 private_data + 58 whitehouse_press_briefings`.
- The raw public transcript / GT / candidate / evaluation artifacts included in this repo cover only `92` public meetings, namely `city_council + whitehouse_press_briefings`.
- The `22` `private_data` meetings are not shared as raw artifacts anywhere in this repo because they contain confidential enterprise data.
- As a result:
  - the aggregate CSV reports still include `private_data` rows;
  - the packaged `meeting-summary/dataset/` tree includes only the public slices;
  - the `20260422` follow-up subdirectory contains derived CSV / Markdown reports only, not raw `private_data` transcript / GT / candidate / evaluation files.

Two more boundaries are important:

- This repo does not contain the full internal implementation. Service modules, prompt/config YAML assets, and other internal pipeline components referenced in the paper are not redistributed here.
- The raw historical logs are also not bundled. The repo includes telemetry exports derived from those logs, not the logs themselves.

## Consistency Checks Already Done

The current package has already been cross-checked on the most important reader-facing points:

- The main paper numbers match the main benchmark CSV:
  - `114` meetings
  - `340` completed meeting-model pairs
  - `680` judge runs
  - the headline means for `gpt-41-mini / gpt-5-mini / gpt-51`
- The `gpt-5.4` vs `gpt-4.1` follow-up bundle matches its own combined report:
  - `56` meetings
  - `112` meeting-model tasks
  - `224` evaluator runs
  - overall and per-slice means
- The Table 5 telemetry values in the paper match [`meeting-summary/measured_stage_level_telemetry_from_logs_20260421_131115.csv`](meeting-summary/measured_stage_level_telemetry_from_logs_20260421_131115.csv)
- [`meeting-summary/gt_agreement_stats_all_20260421.csv`](meeting-summary/gt_agreement_stats_all_20260421.csv) now enumerates all `114` meeting ids, but only the `34` `city_council` meetings contain populated stage-2 alignment statistics; the other slices are represented mainly through coverage and retention-status notes
- Links in the paper Markdown and follow-up bundle README now resolve inside this repo

## How To Read The Packaged Dataset

In the public package, the raw artifacts are stored under `internal/<meeting_id>/...`, and `dataset_type` is carried by the benchmark CSVs rather than by a directory-name level.

Typical paths look like this:

```text
meeting-summary/dataset/assets/transcripts/internal/<meeting_id>/original_transcript.txt
meeting-summary/dataset/views/meeting_notes/ground_truth/internal/<meeting_id>/meetingsummary/ground_truth.json
meeting-summary/dataset/views/meeting_notes/candidate/internal/<meeting_id>/<variant>/<model>/baseline.md
meeting-summary/dataset/views/meeting_notes/evaluation/internal/<meeting_id>/offline/evaluation_report_<variant>_<model>.json
```

In practice:

- In the packaged public `dataset/` tree, `t_*` ids refer to the public `city_council` meetings.
- The `22` `private_data` meeting ids still appear in aggregate CSV / report rows, but their raw transcript / GT / candidate / evaluation files are intentionally absent from `meeting-summary/dataset/`.
- `whpb_*` ids refer to `whitehouse_press_briefings`.
- `ground_truth.json` is the structured GT artifact.
- `baseline.md` is the candidate summary.
- `evaluation_report_*.json` is the offline evaluation result for one meeting and one model.

## About The Legacy Paths Inside CSV Files

Some CSV columns such as `candidate_path`, `gt_path`, and `report_path` still preserve absolute paths from the original execution environment. Those are provenance fields, not the recommended navigation method for this packaged repo.

When reading the public package, prefer:

- this README
- the relative links in the paper Markdown
- [`meeting-summary/gpt54_vs_gpt41_private_citycouncil_20260422/README.md`](meeting-summary/gpt54_vs_gpt41_private_citycouncil_20260422/README.md)

## Fastest Way To Understand The Repo

If you want the shortest path through the package:

1. Read [`meeting-summary/meeting-summary-system-paper_v24.md`](meeting-summary/meeting-summary-system-paper_v24.md)
2. Open [`meeting-summary/meeting_notes_model_comparison_combined_20260417.csv`](meeting-summary/meeting_notes_model_comparison_combined_20260417.csv)
3. Open [`meeting-summary/meeting_notes_model_comparison_combined_significance_20260417.csv`](meeting-summary/meeting_notes_model_comparison_combined_significance_20260417.csv)
4. Read [`meeting-summary/gpt54_vs_gpt41_private_citycouncil_20260422/README.md`](meeting-summary/gpt54_vs_gpt41_private_citycouncil_20260422/README.md)
5. Then drill into the public raw artifacts under `meeting-summary/dataset/`
