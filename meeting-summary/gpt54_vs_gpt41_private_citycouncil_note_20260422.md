# GPT-5.4 vs GPT-4.1 on Private Data and City Council

This note is an insertion-ready supplement for the paper. It does not modify `meeting-summary-system-paper_v22.md`.

## Suggested Placement

This result fits best as a focused supplement after the typed benchmark result sections, for example:

- after Section `6.2 Results by Dataset Type`, as a deployment-oriented follow-up comparison
- or in Section `7 Discussion`, as evidence that a stronger frontier model can improve both retention and factual accuracy on the two operationally important non-White-House slices

## Suggested Paper Text

We also ran a focused two-model comparison on the `private_data` and `city_council` slices only, using the same offline evaluation protocol and the same two judges (`gpt-5-2025-08-07` and `anthropic.claude-sonnet-4-20250514-v1:0`). This comparison covers `56` meetings, `112` completed meeting-model tasks, and `224` evaluator runs. Unlike the broader three-model mixed benchmark, this focused slice comparison does not expose a trade-off between accuracy and retention. `gpt-5.4` improves over `gpt-4.1` on all three core metrics overall: accuracy rises from `0.739` to `0.754`, completeness from `0.789` to `0.844`, and coverage from `0.794` to `0.868`. Exact paired sign tests show that the completeness and coverage gains are robust (`52` vs `3` meeting wins and `41` vs `8` overall, respectively), whereas the accuracy gain remains directional rather than statistically decisive (`30` vs `24`).

The same dominance pattern holds in both constituent dataset types. On `city_council`, `gpt-5.4` improves accuracy from `0.745` to `0.760`, completeness from `0.781` to `0.831`, and coverage from `0.781` to `0.834`. On `private_data`, the gains are larger: accuracy improves from `0.729` to `0.745`, completeness from `0.801` to `0.865`, and coverage from `0.816` to `0.920`. The `private_data` result is especially important because that slice contains dense enterprise coordination content with human-reviewed GT, so the gains are concentrated on a high-value operational regime rather than on a weak-reference subset.

Operationally, this focused result is useful because it removes the main ambiguity present in the broader benchmark. In the larger mixed benchmark, one model family was accuracy-favored while another was retention-favored. In the `private_data + city_council` slice, `gpt-5.4` is descriptively better than `gpt-4.1` on both factual accuracy and information retention, with statistically robust gains on the retention-oriented metrics. That makes the model choice simpler for deployments whose primary workload resembles internal enterprise meetings and city-council proceedings rather than high-density public-affairs briefings.

## Suggested Table

| Scope | Model | Meetings | Evaluator runs | Accuracy | Completeness | Coverage | Mean of 3 metrics |
|---|---|---:|---:|---:|---:|---:|---:|
| overall | `gpt-4.1` | 56 | 112 | 0.739 | 0.789 | 0.794 | 0.774 |
| overall | `gpt-5.4` | 56 | 112 | 0.754 | 0.844 | 0.868 | 0.822 |
| `city_council` | `gpt-4.1` | 34 | 68 | 0.745 | 0.781 | 0.781 | 0.769 |
| `city_council` | `gpt-5.4` | 34 | 68 | 0.760 | 0.831 | 0.834 | 0.808 |
| `private_data` | `gpt-4.1` | 22 | 44 | 0.729 | 0.801 | 0.816 | 0.782 |
| `private_data` | `gpt-5.4` | 22 | 44 | 0.745 | 0.865 | 0.920 | 0.843 |

## Concrete Advantages of GPT-5.4

1. `gpt-5.4` is better on all three core metrics, not just on retention. The overall deltas are `+0.015` accuracy, `+0.055` completeness, and `+0.074` coverage.

2. The gains are stable across both dataset types. This is important because it suggests the improvement is not driven by a single easy slice or by one anomalous regime.

3. The largest gain is on `private_data` coverage (`+0.104`). In practical terms, that points to better retention of owners, dependencies, action items, blockers, and timing details that matter most for enterprise meeting follow-through.

4. `gpt-5.4` also improves accuracy while increasing coverage. That matters because it means the model is not merely producing shorter or more conservative summaries. In fact, it emits more total evaluable claims than `gpt-4.1`, yet still achieves a slightly lower inaccurate-claim rate while covering substantially more GT content.

5. The deployment decision is cleaner than in the broader mixed benchmark. For the two slices most aligned with internal operational use, `gpt-5.4` dominates `gpt-4.1` rather than trading one quality dimension for another.

## Framing Recommendation

The paper should present this as a focused deployment-oriented comparison rather than as a replacement for the main mixed benchmark. The main benchmark still answers the broader scientific question across heterogeneous meeting regimes. This focused result answers a narrower product question: if the target workload is primarily `private_data` plus `city_council`, then `gpt-5.4` is the stronger choice because it improves retention clearly and accuracy directionally under the same evaluation protocol.

## Source Artifacts

- Combined report: [meeting_notes_model_comparison_combined_20260422_134801.csv](/Users/lizhon/PycharmProjects/WebexSuiteAI/dataset-pipeline/report/private_citycouncil_model_comparison_gpt41_gpt54_20260422/full/meeting_notes_model_comparison_combined_20260422_134801.csv)
- Summary note: [meeting_notes_model_comparison_combined_20260422_134801_summary.md](/Users/lizhon/PycharmProjects/WebexSuiteAI/dataset-pipeline/report/private_citycouncil_model_comparison_gpt41_gpt54_20260422/full/meeting_notes_model_comparison_combined_20260422_134801_summary.md)
