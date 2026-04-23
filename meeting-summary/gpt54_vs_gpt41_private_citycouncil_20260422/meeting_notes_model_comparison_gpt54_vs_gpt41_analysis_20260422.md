# GPT-5.4 vs GPT-4.1 Analysis

- Scope: `private_data` + `city_council`
- Comparison unit: paired meeting-level comparison over the same `56` meetings
- Judges: `gpt-5-2025-08-07` and `anthropic.claude-sonnet-4-20250514-v1:0`

## Metric Summary

### overall
- `gpt-4.1`: accuracy `0.739`, completeness `0.789`, coverage `0.794`, mean-of-3 `0.774`
- `gpt-5.4`: accuracy `0.754`, completeness `0.844`, coverage `0.868`, mean-of-3 `0.822`

### city_council
- `gpt-4.1`: accuracy `0.745`, completeness `0.781`, coverage `0.781`, mean-of-3 `0.769`
- `gpt-5.4`: accuracy `0.76`, completeness `0.830`, coverage `0.834`, mean-of-3 `0.808`

### private_data
- `gpt-4.1`: accuracy `0.729`, completeness `0.801`, coverage `0.816`, mean-of-3 `0.782`
- `gpt-5.4`: accuracy `0.745`, completeness `0.865`, coverage `0.92`, mean-of-3 `0.843`

## Meeting-Level Win Counts

### overall
- `accuracy`: `gpt-5.4` wins `30`, `gpt-4.1` wins `24`, ties `2`, avg delta `0.015232`, exact sign-test p `0.496617`
- `completeness`: `gpt-5.4` wins `52`, `gpt-4.1` wins `3`, ties `1`, avg delta `0.054732`, exact sign-test p `1.5418777365994174e-12`
- `coverage`: `gpt-5.4` wins `41`, `gpt-4.1` wins `8`, ties `7`, avg delta `0.073625`, exact sign-test p `2e-06`

### city_council
- `accuracy`: `gpt-5.4` wins `17`, `gpt-4.1` wins `15`, ties `2`, avg delta `0.014618`, exact sign-test p `0.86005`
- `completeness`: `gpt-5.4` wins `31`, `gpt-4.1` wins `2`, ties `1`, avg delta `0.049059`, exact sign-test p `1.3085082173347473e-07`
- `coverage`: `gpt-5.4` wins `22`, `gpt-4.1` wins `5`, ties `7`, avg delta `0.053647`, exact sign-test p `0.001514`

### private_data
- `accuracy`: `gpt-5.4` wins `13`, `gpt-4.1` wins `9`, ties `0`, avg delta `0.016182`, exact sign-test p `0.523467`
- `completeness`: `gpt-5.4` wins `21`, `gpt-4.1` wins `1`, ties `0`, avg delta `0.0635`, exact sign-test p `1.1e-05`
- `coverage`: `gpt-5.4` wins `19`, `gpt-4.1` wins `3`, ties `0`, avg delta `0.1045`, exact sign-test p `0.000855`

## Why GPT-5.4 Is Better

### overall
- `gpt-4.1` claim profile: inaccurate claims `725` / total claims `2794`; uncovered GT points `599` / total GT points `2992`; detail distribution `rich=559`, `adequate=1456`, `sparse=270`, `barebone=29`; top issue labels: unsupported_by_gt=334, factual_error=162, fabricated_facts=121, changed_nature=56
- `gpt-5.4` claim profile: inaccurate claims `982` / total claims `3972`; uncovered GT points `317` / total GT points `2977`; detail distribution `rich=1269`, `adequate=1301`, `sparse=88`, `barebone=3`; top issue labels: unsupported_by_gt=513, fabricated_facts=264, factual_error=147, contradicts_gt=24

### city_council
- `gpt-4.1` claim profile: inaccurate claims `347` / total claims `1374`; uncovered GT points `350` / total GT points `1694`; detail distribution `rich=309`, `adequate=807`, `sparse=159`, `barebone=17`; top issue labels: unsupported_by_gt=160, fabricated_facts=76, factual_error=63, changed_nature=23
- `gpt-5.4` claim profile: inaccurate claims `507` / total claims `2098`; uncovered GT points `221` / total GT points `1679`; detail distribution `rich=694`, `adequate=709`, `sparse=50`, `barebone=1`; top issue labels: unsupported_by_gt=246, fabricated_facts=158, factual_error=78, changed_certainty=13

### private_data
- `gpt-4.1` claim profile: inaccurate claims `378` / total claims `1420`; uncovered GT points `249` / total GT points `1298`; detail distribution `rich=250`, `adequate=649`, `sparse=111`, `barebone=12`; top issue labels: unsupported_by_gt=174, factual_error=99, fabricated_facts=45, changed_nature=33
- `gpt-5.4` claim profile: inaccurate claims `475` / total claims `1874`; uncovered GT points `96` / total GT points `1298`; detail distribution `rich=575`, `adequate=592`, `sparse=38`, `barebone=2`; top issue labels: unsupported_by_gt=267, fabricated_facts=106, factual_error=69, contradicts_gt=16

## Main Interpretation

- `gpt-5.4` outperforms `gpt-4.1` on all three core metrics overall and in both dataset types; this is not a retention-only gain.
- The strongest gain is retention on `private_data`, especially coverage (`0.920` vs `0.816`). This is consistent with fewer uncovered GT points and many more `rich` completeness judgments under `gpt-5.4`.
- The accuracy gain is smaller than the retention gain, but it is directionally consistent in both slices. `gpt-5.4` does not reduce the absolute number of inaccurate claims; instead, it produces substantially more total claims while still achieving a lower inaccurate-claim rate and much higher GT coverage. The gain is therefore not caused by producing shorter or more conservative summaries.
- On `city_council`, `gpt-5.4` mainly improves completeness and coverage while still preserving a small accuracy advantage. On `private_data`, it improves all three metrics more clearly, suggesting better handling of owner/action/dependency/timeline-heavy internal meeting content.
- The error profile is still dominated by `unsupported_by_gt` rather than direct contradiction, so the comparison should be interpreted as an improvement in grounded retention under the current GT rubric rather than as a claim that `gpt-5.4` eliminates factual risk.
