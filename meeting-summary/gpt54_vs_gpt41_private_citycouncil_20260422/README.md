# GPT-5.4 vs GPT-4.1 Artifact Bundle

This folder packages the focused `gpt-5.4` versus `gpt-4.1` comparison for the `private_data` and `city_council` slices only.

The bundle includes the derived CSV and Markdown artifacts needed to inspect the result. The original run-summary JSON files stayed in the source execution workspace and are not redistributed here.

This is a report-only bundle. The `22` `private_data` meetings included in the comparison are represented only through aggregate and meeting-level report rows inside the packaged CSV / Markdown outputs. No raw `private_data` transcripts, GT JSON, candidate summaries, or evaluation JSON are redistributed here or under [`meeting-summary/dataset/`](../dataset/).

## Included Artifacts

- [meeting_notes_model_comparison_combined_20260422_134801.csv](meeting_notes_model_comparison_combined_20260422_134801.csv)
- [meeting_notes_model_comparison_overall_by_model_20260422_134801.csv](meeting_notes_model_comparison_overall_by_model_20260422_134801.csv)
- [meeting_notes_model_comparison_overall_by_model_dataset_type_20260422_134801.csv](meeting_notes_model_comparison_overall_by_model_dataset_type_20260422_134801.csv)
- [meeting_notes_model_comparison_gpt54_vs_gpt41_significance_20260422.csv](meeting_notes_model_comparison_gpt54_vs_gpt41_significance_20260422.csv)
- [meeting_notes_model_comparison_gpt54_vs_gpt41_analysis_20260422.md](meeting_notes_model_comparison_gpt54_vs_gpt41_analysis_20260422.md)
- [run_report_20260422.md](run_report_20260422.md)

## Recommended Reading Order

1. Start with [meeting_notes_model_comparison_overall_by_model_20260422_134801.csv](meeting_notes_model_comparison_overall_by_model_20260422_134801.csv) for the top-line model comparison.
2. Then read [meeting_notes_model_comparison_overall_by_model_dataset_type_20260422_134801.csv](meeting_notes_model_comparison_overall_by_model_dataset_type_20260422_134801.csv) to see whether the gains hold in both `private_data` and `city_council`.
3. Use [meeting_notes_model_comparison_gpt54_vs_gpt41_significance_20260422.csv](meeting_notes_model_comparison_gpt54_vs_gpt41_significance_20260422.csv) for meeting-level win counts and exact paired sign tests.
4. Use [meeting_notes_model_comparison_gpt54_vs_gpt41_analysis_20260422.md](meeting_notes_model_comparison_gpt54_vs_gpt41_analysis_20260422.md) for mechanism-level interpretation.
5. Use [meeting_notes_model_comparison_combined_20260422_134801.csv](meeting_notes_model_comparison_combined_20260422_134801.csv) when you need both the aggregate rows and the meeting-level detail in one file.

## Scope

- Dataset types: `private_data`, `city_council`
- Candidate models: `gpt-4.1`, `gpt-5.4`
- Meetings: `56`
- Evaluator runs: `224`

## Main Takeaway

`gpt-5.4` is descriptively stronger than `gpt-4.1` on all three core metrics in this focused slice comparison. The completeness and coverage advantages are broad meeting-level effects and statistically robust, while the accuracy gain is smaller and should be treated as directional.

## Practical Interpretation

- This bundle is best used as a deployment-oriented supplement to the main mixed benchmark, not as a replacement for it.
- The strongest practical advantage of `gpt-5.4` is higher retention without a directional accuracy penalty.
- The biggest lift appears on `private_data`, especially coverage, which matters for action items, owners, blockers, and timeline details.
- The mechanism is not simple conservatism: `gpt-5.4` says more, covers more GT content, and still keeps a slightly lower inaccurate-claim rate.
