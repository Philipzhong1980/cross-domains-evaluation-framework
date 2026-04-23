# Evaluating AI Meeting Summaries with a Reusable Cross-Domain Pipeline

Philip Zhong, Don Wang, Jason Zhang, Kent Chen  

Webex Suite AI  
Cisco Systems, Inc.  
San Jose, California, USA  

{lizhon, dongdwan, xiaojzha, weiwchen}@cisco.com

## Abstract

We present a reusable evaluation pipeline for generative-AI applications and instantiate it for AI meeting summaries in the Dataset Pipeline repository. The system factors evaluation into five stages: source intake, structured reference construction, candidate generation, structured scoring, and persisted reporting. Two design choices distinguish it from standalone claim scorers: ground truth is generated and stored as typed meeting artifacts, and evaluator outputs are stored as structured score artifacts that support aggregation, issue analysis, and statistical testing. We benchmark the offline loop on a merged typed benchmark of `114` meetings across `city_council`, `private_data`, and `whitehouse_press_briefings`, yielding `340` completed meeting-model pairs and `680` judge runs for `gpt-41-mini`, `gpt-5-mini`, and `gpt-51`. `gpt-41-mini` attains the highest mean accuracy (`0.584`), while `gpt-51` leads on completeness (`0.886`) and coverage (`0.942`). Exact paired sign tests with Holm correction show no statistically significant accuracy winner, but significant retention advantages for `gpt-51`. The typed benchmark also reveals a domain-specific failure regime: White House briefings are much harder on accuracy not because GT is larger, but because summary generation and claim extraction introduce more unsupported specifics under a coarser reference regime. The offline loop is fully benchmarked in this paper; the online loop remains a designed extension for future production-feedback integration.

## 1. Introduction

AI meeting summaries are often evaluated by prompt iteration and qualitative spot checks. That workflow is rarely sufficient for deployment. Model upgrades can silently degrade factual quality, improvements in one aspect of summary behavior can mask regressions in another, and production-facing failures are usually structured rather than anecdotal: unsupported additions, omitted actions, role confusion, or over-committed certainty.

The broader systems problem is not limited to meeting summarization. Teams typically need evaluation evidence for multiple generative-AI products, including search, summarization, assistants, and question answering. If each product builds its own evaluation stack from scratch, the organization loses comparability, inspectability, and operational reuse. This paper argues that the reusable unit should be the **evaluation pipeline**: artifact construction, controlled candidate generation, automated comparison, persisted explanations, and release-facing reporting. The roadmap perspective makes this even more concrete: a dependable AI quality loop needs reusable control points for data simulation or collection, dataset construction, offline benchmarking, CI/CD gating, and online feedback.

This work directly extends *Evaluating Embedding Models and Pipeline Optimization for AI Search Quality* by Zhong, Chen, and Wang ([arXiv:2511.22240](https://arxiv.org/abs/2511.22240)). That earlier paper established a reusable pipeline pattern for AI search through curated evaluation data, automated benchmarking, and deployment-oriented comparison of system variants. The present paper instantiates the same pattern for AI meeting summaries, where the reference artifact becomes structured meeting-summary ground truth and the comparison layer becomes claim-grounded factual scoring over generated summaries.

The present paper is written as a **system paper**. Its contribution is not a new factuality metric in isolation, but a reusable evaluation substrate implemented in the Dataset Pipeline repository. The empirical section uses the meeting-summary instantiation of that substrate to show what the pipeline produces in practice: durable artifacts, typed benchmark partitions, structured GT and structured score generation, statistically grounded release evidence, reusable error analysis, and explicit quality-loop support for benchmarking, regression detection, and failure-case discovery.

Relative to the earlier AI-search paper, the present work contributes three new system elements. First, it elevates **structured GT generation** into an explicit pipeline stage rather than assuming static reference data. Second, it introduces **typed benchmark partitioning**, which makes it possible to surface domain-specific failure regimes rather than only merged averages. Third, it adds **claim-level structured scoring with formal metric definitions**, which in turn enables the anomaly diagnosis in Section 6.2 and the significance-backed model-selection analysis in Section 6.3. These additions are not cosmetic extensions of the earlier pipeline; they are the mechanisms that make the meeting-summary benchmark diagnostically useful.

The main contributions are:

1. a five-stage reusable evaluation control loop (source intake → structured reference construction → candidate generation → structured scoring → persisted reporting) that enables cross-domain reuse by separating orchestration from task-specific reference schemas, demonstrated across AI search and AI meeting summarization
2. an implemented meeting-summary evaluation stack with transcript-backed storage, structured GT construction, structured score generation, candidate generation, offline evaluation, and persisted reporting
3. an expanded typed benchmark over 114 meetings and three candidate models, including dataset-type breakdowns, meeting-level significance testing, and evaluator disagreement analysis

## 2. Design Goals and Cross-Domain Reuse

The design is driven by four system goals.

### 2.1 G1: Inspectable Artifacts

Every major object in the pipeline should be auditable after execution: source transcript, GT, candidate summary, judge outputs, and report. This favors file-backed persistence over ephemeral evaluation runs.

### 2.2 G2: Reusable Orchestration, Task-Specific References

The orchestration layer should be reusable across AI tasks even when the reference artifact changes. In AI search, the reference is query-document relevance. In meeting summarization, the reference is structured GT over meeting topics, points, and decisions. The pipeline should keep the orchestration stable while swapping the task-specific reference layer and metric definitions.

### 2.3 G3: Release-Oriented Comparison

The pipeline should support repeated comparison of candidate systems under a controlled protocol, so that model-selection decisions are backed by persisted evidence rather than one-off manual review.

### 2.4 G4: Extensibility from Offline to Online Quality Loops

The implemented core in this paper is the offline loop. However, the architecture should also support a future online path in which production issues can be clustered, curated, and turned into new benchmark items. In this sense, the system is designed not only for evaluation but for evaluation maintenance.

These goals yield a clean cross-domain abstraction. The reusable skeleton is:

- persist source artifacts rather than treating them as transient inputs
- construct task-specific reference artifacts under version control
- generate or ingest candidate outputs under controlled configurations
- evaluate candidates with structured, inspectable outputs
- persist reports for model selection, regression tracking, and future dataset improvement

Two properties are especially important in the present meeting-summary instantiation.

- **structured GT generation**: the repository does not treat GT as an opaque annotation blob; it generates and persists typed meeting objects
- **structured score generation**: the evaluator does not emit only a single free-form judgment; it emits claim-level alignments, per-metric scores, explanations, and issue labels that can be aggregated later

This design also aligns with the internal roadmap concepts behind the broader AI datasets and evaluation program:

- **golden seed data**: high-quality reference artifacts anchor trustworthy benchmarking
- **dataset synthesis and quality assurance**: data generation is paired with validation rather than treated as a blind scaling step
- **evaluation orchestration**: repeated runs are controlled by a common execution pattern
- **evaluation metrics and insights**: the system must produce not only scores, but diagnosis and actionable model-selection signals

### 2.5 Positioning Against General-Purpose Evaluation Frameworks

General-purpose evaluation frameworks such as RAGAS [10, 11], TruLens [12], and DeepEval [13] solve adjacent problems and are valuable points of comparison. RAGAS emphasizes reusable metrics and synthetic testset generation. TruLens emphasizes feedback functions, tracing, and ground-truth agreement. DeepEval emphasizes metric libraries, local test execution, and CI/CD-oriented LLM testing. The present system overlaps with all three, but its scope is different: it treats structured GT construction, structured score generation, typed benchmark partitioning, and persisted release-facing artifacts as first-class pipeline stages rather than optional surrounding infrastructure.

The comparison in Table 0 is architectural rather than exhaustive. It is intended to clarify system scope, not to claim that other frameworks cannot be extended. Capabilities evolve quickly; the table summarizes the official literature where available and otherwise the official software documentation cited in the references as accessed on April 17, 2026. We do not claim an empirical head-to-head evaluation against these systems in the present paper; that comparison is deferred to future work.

| Capability dimension | This system | RAGAS | TruLens | DeepEval | Standalone claim scorer |
|---|---|---|---|---|---|
| File-backed end-to-end artifacts | Yes | No | Partial | Partial | No |
| Reusable cross-domain architecture | Yes | Partial | Partial | Partial | No |
| Structured GT generation stage | Yes | Partial | No | No | No |
| Meeting-summary-specific typed schema and metrics | Yes | No | No | Partial | Partial |
| Typed dataset partitions | Yes | No | No | No | No |
| Release-gating / regression reports | Yes | No | No | Partial | No |
| Multi-model comparison reports | Yes | Partial | Partial | Partial | No |
| CI/CD quality-gate path | Yes | No | No | Partial | No |

## 3. System Architecture

The repository is not itself a meeting assistant product. It is the evaluation and artifact layer that supports one.

![Dual-loop quality framework](/Users/lizhon/PycharmProjects/WebexSuiteAI/dataset-pipeline/paper/dual_loop_quality_framework.svg)

Figure 1. Reusable quality-loop architecture for AI meeting-summary evaluation. Solid components correspond to the benchmarked offline loop. The dashed online loop is implemented as system context but is not benchmarked in this paper.

Figure 1 shows the high-level architecture. Read through the roadmap lens, the loop consists of five reusable stages: a transcript simulator or production-data intake layer, a dataset generator, an offline evaluation stage, a CI/CD quality gate, and an online evaluation stage. The offline loop provides benchmark-backed regression control and is the portion validated directly in this paper. The online loop is shown as a dashed, designed-but-not-yet-benchmarked extension: it captures production-facing signals and feeds them into later dataset expansion, but it is included here as system context rather than as a fully validated experimental component.

The implemented repository includes:

- transcript-backed artifact storage
- prompt-versioned ground-truth generation
- prompt-versioned candidate generation
- offline evaluation against GT with structured judge outputs
- entry points for online and grounded evaluation
- file-backed reports that remain inspectable after execution

These components collectively support the three concrete benefits emphasized in the roadmap:

- **benchmarking performance** under a stable protocol
- **regression detection** when models, prompts, or features change
- **failure-case discovery** through persisted explanations and issue labels

![Repository pipeline implementation](/Users/lizhon/PycharmProjects/WebexSuiteAI/dataset-pipeline/paper/repository_pipeline_implementation.svg)

Figure 2. Repository-level realization of the five-stage control loop. Transcript assets feed both GT construction and candidate generation; offline evaluation consumes `(GT, candidate)` pairs and emits structured reports for comparison and release-facing analysis.

Figure 2 grounds the design in the current repository. Unlike Figure 1, which is architectural, this view maps directly to persisted artifacts and the scripts used in the benchmark workflow.

The two figures should be read together. In Figure 1, Stage 1 source intake corresponds to the transcript assets, Stage 2 structured reference construction corresponds to GT generation, Stage 3 candidate generation corresponds to application-facing summary generation, Stage 4 structured scoring corresponds to offline evaluation, and Stage 5 persisted reporting corresponds to the benchmark and release-report layer. In Figure 2, the transcript curation node takes raw transcript files as input and outputs normalized transcript assets. The GT construction node takes those transcript assets and outputs typed JSON structured around `meeting_context`, `participants`, `topics`, `points`, and `decisions`. The candidate-generation node takes the same transcript assets and outputs application-mirroring markdown summaries. The offline-evaluation node takes `(GT artifact, candidate artifact)` pairs and outputs structured evaluation JSON containing extracted claims, per-metric scores, issue labels, and explanations. This topology is deliberate: transcripts feed both GT and candidates so that reference construction and candidate generation remain comparable, while reporting stays downstream of structured scoring so that the same aggregation logic can be reused across domains.

## 4. Pipeline Components

### 4.1 Artifact Model

The repository persists meeting-summary artifacts in a file-backed layout:

```text
dataset/
├── assets/transcripts/<meeting_type>/<meeting_id>/original_transcript.txt
└── views/meeting_notes/
    ├── ground_truth/<meeting_type>/<meeting_id>/meetingsummary/ground_truth.json
    ├── candidate/<meeting_type>/<meeting_id>/<variant>/<model>/baseline.md
    └── evaluation/<meeting_type>/<meeting_id>/offline/evaluation_report_<variant>.json
```

This layout matters systemically because it makes every stage independently inspectable. Transcript, GT, candidate, and evaluator outputs can all be audited or regenerated without ambiguity. It also makes cross-domain reuse practical: the repository can keep the same orchestration while swapping task-specific reference artifacts. In roadmap terms, this is what allows the same quality loop to be aligned by different teams while preserving a common evaluation substrate.

In this paper, **candidate** has a specific operational meaning: it is the application-generated meeting summary being evaluated against GT. In the current benchmark, candidates are produced by a repository pipeline that mirrors product behavior rather than by replaying production logs directly, but analytically they still represent the application's summary output.

### 4.2 Ground-Truth Construction

The meeting-summary GT is organized around:

- `meeting_context`
- `participants`
- `topics`
- `points`
- `decisions`

Point identifiers such as `t_001_p_001` are assigned after the semantic structure is generated. This preserves a stable downstream schema while keeping the generation stage focused on meeting content rather than identifier formatting.

This is a core systems property of the paper: GT is generated as a **structured representation**, not merely as untyped prose. That structured representation is what later enables stable claim alignment, metric aggregation, and typed benchmark analysis.

The benchmarked GT path is fully automated in the current repository. `GroundTruthService` calls `MeetingSummaryGroundTruthGenerator.generate_ground_truth_advanced()`, which executes a multi-stage pipeline rather than a single-pass extraction. Stage 1 generates two independent draft GTs with `gt_generation_v6.yaml`, one using `gpt-5-2025-08-07` and one using `anthropic.claude-sonnet-4-20250514-v1:0`. Stage 2 aligns these drafts with `generation_alignment_v3.yaml`. Stage 3 re-reviews both uncertain and single-aligned items with `generation_review_uncertain_v2.yaml` and `generation_review_single_align_v2.yaml`. Stage 4 merges the aligned and reviewed material with `generation_final_merge_v2.yaml`, after which the repository assigns stable `t_###_p_###` and `d_###` identifiers and recomputes metadata counters.

All stages are executed through JSON-schema-constrained prompts and cached as intermediate artifacts. Quality control is therefore machine-based rather than human-based: schema-constrained generation, dual-model draft comparison, targeted review of uncertain items, identifier normalization, metadata recomputation, and an optional audit path all act as guards on GT consistency. The repository also exposes an optional audit stage (`gt_audit_v3.yaml`) that scores GT faithfulness and coverage against the transcript, but that audit is not a mandatory gate for every benchmark item in the present study. Importantly, the default benchmark path does **not** include a required human-review stage. The benchmark should therefore be interpreted as using machine-generated and partially machine-audited structured GT.

The same automated GT pipeline is used across `city_council`, `private_data`, and `whitehouse_press_briefings`; there are no subset-specific model swaps in the reported benchmark. The main subset difference is artifact normalization. `city_council` and `private_data` GT files persist metadata counters directly, whereas all `whitehouse_press_briefings` GT files retain the same structured topics and points but omit stored metadata counters, so evaluation traverses topics, points, and decisions at runtime. This distinction matters for interpretation and is revisited in Sections 6.2 and 6.6.

Two transparency notes matter for interpretation. First, the repository does retain intermediate alignment artifacts for a subset of meetings (`36` stage-2 alignment temp directories in the current workspace), which confirms that full agreement, single-aligned items, and conflict/uncertain items all occur in practice. However, these temp artifacts are not retained uniformly across the full 114-meeting benchmark, so the paper does not report benchmark-wide alignment percentages as if they were fully normalized statistics. Second, retained audit artifacts are present for `20` meetings, but the audit stage was not enforced as a mandatory gate across all benchmark items. In other words, the benchmark is based on machine-generated structured GT with partial machine-audit retention rather than universal audit-gated reference construction.

### 4.3 Candidate Generation

For this study, each meeting is summarized under the same candidate pipeline:

- summary style: `standard`
- candidate filename: `baseline.md`
- fixed prompt family: `standard_v1.yaml` + `format_v1.yaml`

This design isolates **model choice under a fixed prompt pipeline** rather than conflating model differences with prompt tuning. The three candidate-generation models are:

| Report label | Backing model |
|---|---|
| `gpt-41-mini` | `gpt-4.1-mini` |
| `gpt-5-mini` | `gpt-5-mini-2025-08-07` |
| `gpt-51` | `gpt-5.1` |

### 4.4 Offline Evaluator and Metrics

The offline evaluator compares candidate summaries against GT through three factual metrics. The pipeline first extracts candidate claims with a fixed claim-extraction prompt family (`claims_v2.yaml`) and a fixed extractor model (`gpt-5-2025-08-07`). Those claims are then scored against GT by metric-specific evaluators.

| Metric | Operational meaning |
|---|---|
| Accuracy | The fraction of extracted candidate claims judged accurate when compared to GT |
| Completeness | The average detail-retention score over GT items that were already marked covered by the candidate summary |
| Coverage | The fraction of GT items marked covered by the candidate summary |

These conceptual definitions are implemented through structured verdicts rather than free-form scoring. Let `C = {c1, ..., cm}` be the extracted claim set from a candidate summary and `G = {g1, ..., gn}` be the GT point/decision set used by the evaluator. Each candidate claim receives a verdict `v(ci) in {accurate, inaccurate}`. Each GT item receives a coverage state `s(gj) in {covered, uncovered}`. For covered GT items, the completeness evaluator additionally assigns a detail score `d(gj) in [0, 1]` and a detail level `l(gj) in {rich, adequate, sparse, barebone}`.

```text
Accuracy(C, G)      = (1 / m) * Σ 1[v(ci) = accurate]
Coverage(C, G)      = (1 / n) * Σ 1[s(gj) = covered]
Completeness(C, G)  = (1 / |Gcov|) * Σ d(gj),   Gcov = {gj : s(gj) = covered}
```

This means that `Coverage` is a binary core-content metric, whereas `Completeness` is a detail-retention metric conditioned on GT items that were already marked covered. When no GT items are covered, completeness is defined operationally as `0`. Because completeness is conditional on coverage, the two metrics are not recall variants of one another: a model can cover many GT items but still summarize them sparsely, in which case coverage can be numerically higher than completeness.

For interpretation, the repository supports a three-way reading:

- **fully captured**: the GT item is covered and receives a `rich` or `adequate` detail level
- **partially captured**: the GT item is covered but receives a `sparse` or `barebone` detail level
- **missing**: the GT item is uncovered

A simple example is a GT point such as “The committee approved the extension through June 2026.” A candidate that says “The committee approved the extension through June 2026” is fully captured; “The committee approved the extension” is partially captured because it omits the deadline; and a candidate that never mentions the extension is missing. Operationally, the first two cases are both counted as `covered` by the coverage evaluator, but they receive different completeness detail scores.

The framework remains compatible with claim-based evaluation: candidate summaries are decomposed into factual units and aligned against grounded reference content. The system-level contribution is that claim-grounded checking is embedded in a larger operational artifact pipeline rather than used only as a standalone scorer.

Equally important, score generation is itself **structured**. The evaluator does not stop at a single scalar judgment. It produces:

- metric-specific scores
- claim-alignment outputs
- explanations for each metric
- issue labels such as `unsupported_by_gt`, `fabricated_facts`, and `missing`

This structure is what makes later aggregation, significance testing, typed dataset comparison, and release reporting possible.

## 5. Evaluation Methodology

### 5.1 Benchmark Universe

The merged typed benchmark used in this study contains `114` unique meetings across three dataset types:

- `city_council`: `34` meetings
- `private_data`: `22` meetings
- `whitehouse_press_briefings`: `58` meetings

At the meeting-model-pair level, the merged report contains:

- `340` completed meeting-model pairs
- `680` evaluator runs

The count is not `342` because one `city_council` meeting currently contains only the `gpt-41-mini` candidate/report pair; the `gpt-5-mini` and `gpt-51` outputs are missing for that meeting. As a result, the overall benchmark contains `114` meetings, but the paired three-model comparisons in Section 6.3 operate on `113` meetings.

The typed structure of the benchmark matters for system evaluation. It allows the same pipeline to be assessed not only overall, but also by dataset type, which exposes where the system is stable across categories and where task difficulty shifts.

### 5.2 Judges and Aggregation

Each candidate summary is evaluated against GT by two judges:

- `gpt-5-2025-08-07`
- `anthropic.claude-sonnet-4-20250514-v1:0`

This yields:

- `340` completed meeting-model pairs
- `680` evaluator runs

For each meeting-model pair, the pipeline stores:

- judge-specific scores
- explanations for each metric
- structured issue labels
- averaged `accuracy_avg`, `completeness_avg`, and `coverage_avg`

The aggregate report used in this paper is:

- [meeting_notes_model_comparison_combined_20260417.csv](/Users/lizhon/PycharmProjects/WebexSuiteAI/dataset-pipeline/paper/meeting_notes_model_comparison_combined_20260417.csv)

### 5.3 Evaluation Protocol

The offline evaluation protocol follows five steps.

1. For each transcript-GT pair, the repository generates one candidate summary per model under the same prompt family.
2. The evaluator decomposes the candidate summary into factual units suitable for claim-level comparison.
3. Two judges independently align those candidate claims against GT topics, points, and decisions.
4. The pipeline stores judge-specific scores, explanations, and issue labels.
5. The benchmark report averages the two judges per meeting-model pair and then aggregates those averages across the merged typed benchmark.

### 5.4 Statistical Testing

To complement descriptive averages, we perform **exact paired two-sided sign tests** on meeting-level model comparisons for each metric. The comparison unit is the meeting. For any model pair and metric, each meeting contributes one win, one loss, or one tie; ties are excluded from the test. Because each metric induces three pairwise model comparisons, we apply **Holm correction** within each metric family.

This test is intentionally conservative. It does not use score magnitude; it asks whether one model wins significantly more meetings than another under the paired benchmark design. That framing fits the system use case because model releases are decided over repeated meeting-level comparisons rather than over a single pooled score.

The significance summary used in this paper is:

- [meeting_notes_model_comparison_combined_significance_20260417.csv](/Users/lizhon/PycharmProjects/WebexSuiteAI/dataset-pipeline/paper/meeting_notes_model_comparison_combined_significance_20260417.csv)

### 5.5 Operational Telemetry

The repository does instrument runtime telemetry at the service level. Job duration, API latency, LLM token usage, and LLM latency are emitted through the structured logging helpers in `log_config.metrics`. However, the current 114-meeting benchmark is assembled from historical runs that were not normalized into one cost-and-latency ledger across all meetings and stages. We therefore report benchmark quality results in this paper, but not a benchmark-wide cost table. A normalized operational-cost report is a concrete next step for the system.

## 6. Experimental Evaluation

### 6.1 Main Benchmark Results

Table 1 reports the main merged typed benchmark result over `114` meetings, `340` completed meeting-model pairs, and `680` evaluator runs.

| Model | Meetings | Evaluator runs | Accuracy | Completeness | Coverage | Mean of 3 metrics |
|---|---:|---:|---:|---:|---:|---:|
| `gpt-41-mini` | 114 | 228 | 0.584 | 0.814 | 0.804 | 0.734 |
| `gpt-5-mini` | 113 | 226 | 0.574 | 0.843 | 0.875 | 0.764 |
| `gpt-51` | 113 | 226 | 0.553 | 0.886 | 0.942 | 0.794 |

The primary pattern is still a structured trade-off, but the larger mixed benchmark changes the frontier. `gpt-41-mini` now has the highest mean accuracy, while `gpt-51` remains clearly best on completeness and coverage. `gpt-5-mini` occupies the middle ground on retention-oriented metrics but no longer leads on accuracy once the typed benchmark is expanded.

### 6.2 Results by Dataset Type

Because the benchmark is typed, the merged result can also be broken down by data category.

| Dataset type | Model | Meetings | Accuracy | Completeness | Coverage |
|---|---|---:|---:|---:|---:|
| `city_council` | `gpt-41-mini` | 34 | 0.703 | 0.775 | 0.775 |
| `city_council` | `gpt-5-mini` | 33 | 0.709 | 0.820 | 0.860 |
| `city_council` | `gpt-51` | 33 | 0.688 | 0.878 | 0.896 |
| `private_data` | `gpt-41-mini` | 22 | 0.704 | 0.805 | 0.838 |
| `private_data` | `gpt-5-mini` | 22 | 0.724 | 0.850 | 0.869 |
| `private_data` | `gpt-51` | 22 | 0.700 | 0.889 | 0.957 |
| `whitehouse_press_briefings` | `gpt-41-mini` | 58 | 0.467 | 0.841 | 0.807 |
| `whitehouse_press_briefings` | `gpt-5-mini` | 58 | 0.440 | 0.853 | 0.886 |
| `whitehouse_press_briefings` | `gpt-51` | 58 | 0.420 | 0.889 | 0.963 |

Two patterns stand out. First, the ranking on completeness and coverage is stable across all three dataset types: `gpt-51` is consistently strongest, followed by `gpt-5-mini`, then `gpt-41-mini`. Second, accuracy is much more dataset-sensitive. The `whitehouse_press_briefings` slice is substantially harder on accuracy for all models, which is what shifts the overall merged typed benchmark away from the earlier smaller benchmark's accuracy ordering.

This anomaly is important because it is not explained by larger GT size. In the current benchmark, `whitehouse_press_briefings` averages about `26.34` GT items per meeting, compared with roughly `30.15` for `city_council` and `36.36` for `private_data`. The harder accuracy behavior instead comes from claim overproduction: in the White House slice, `gpt-41-mini` averages about `29.74` extracted claims and `15.92` inaccurate claims per meeting-model pair, `gpt-5-mini` averages `38.81` and `21.60`, and `gpt-51` averages `42.48` and `23.95`. The dominant White House issue labels are `unsupported_by_gt` (`3930`) and `fabricated_facts` (`2531`), far outweighing direct contradiction.

The key systems conclusion is therefore not that White House GT is simply larger or that one model is uniquely unstable. The typed benchmark shows a distinct failure regime in which public-affairs summaries produce more unsupported specifics than the corresponding GT can absorb. In practical terms, accuracy collapses there because transcript-faithful candidate details are evaluated against a coarser reference representation. Section 7.1 analyzes this mismatch in more detail and explains why the same prompt family behaves much better on `private_data` and `city_council`.

### 6.3 Meeting-Level Wins and Statistical Significance

Aggregate means can hide whether gains are broad or driven by a few outliers. We therefore report meeting-level wins over the `113` meetings for which all three model outputs are available in the merged report.

| Metric | `gpt-41-mini` wins | `gpt-5-mini` wins | `gpt-51` wins | Ties |
|---|---:|---:|---:|---:|
| Accuracy | 48 | 36 | 26 | 3 |
| Completeness | 3 | 9 | 100 | 1 |
| Coverage | 0 | 10 | 82 | 21 |

The completeness and coverage advantages of `gpt-51` remain broad meeting-level effects rather than mean-value artifacts. Accuracy is different: the three models remain much closer, and the merged typed benchmark no longer supports a statistically decisive winner.

Table 2 reports the paired sign tests. Positive mean differences indicate that model `A` outperforms model `B` on the given metric. Ties are excluded from the sign tests. Holm correction is applied within each metric family across the three pairwise comparisons.

| Metric | Comparison | Mean diff (A-B) | Meeting wins (A / ties / B) | Holm-adjusted p | Significant at 0.05 |
|---|---|---:|---:|---:|---|
| Accuracy | `gpt-41-mini` vs `gpt-5-mini` | 0.006 | 60 / 2 / 51 | 0.447806 | No |
| Accuracy | `gpt-41-mini` vs `gpt-51` | 0.027 | 69 / 1 / 43 | 0.053297 | No |
| Accuracy | `gpt-5-mini` vs `gpt-51` | 0.021 | 64 / 2 / 47 | 0.256951 | No |
| Completeness | `gpt-41-mini` vs `gpt-5-mini` | -0.028 | 20 / 2 / 91 | 5.25 × 10^-12 | Yes |
| Completeness | `gpt-41-mini` vs `gpt-51` | -0.071 | 3 / 1 / 109 | 2.71 × 10^-28 | Yes |
| Completeness | `gpt-5-mini` vs `gpt-51` | -0.043 | 9 / 1 / 103 | 4.63 × 10^-21 | Yes |
| Coverage | `gpt-41-mini` vs `gpt-5-mini` | -0.072 | 15 / 21 / 77 | 3.26 × 10^-11 | Yes |
| Coverage | `gpt-41-mini` vs `gpt-51` | -0.139 | 3 / 11 / 99 | 2.09 × 10^-25 | Yes |
| Coverage | `gpt-5-mini` vs `gpt-51` | -0.067 | 11 / 17 / 85 | 5.10 × 10^-15 | Yes |

This result sharpens the descriptive interpretation. The apparent overall accuracy lead of `gpt-41-mini` is not statistically significant after Holm correction. By contrast, the completeness and coverage advantages of `gpt-51` are statistically significant against both alternatives, and `gpt-5-mini` also significantly exceeds `gpt-41-mini` on those retention-oriented metrics.

### 6.4 Judge Variance

Because the benchmark uses two judges, model means should be interpreted together with judge spread.

| Model | Judge | Accuracy | Completeness | Coverage |
|---|---|---:|---:|---:|
| `gpt-41-mini` | Claude Sonnet 4 | 0.628 | 0.822 | 0.824 |
| `gpt-41-mini` | GPT-5 judge | 0.540 | 0.807 | 0.784 |
| `gpt-5-mini` | Claude Sonnet 4 | 0.616 | 0.836 | 0.897 |
| `gpt-5-mini` | GPT-5 judge | 0.531 | 0.850 | 0.854 |
| `gpt-51` | Claude Sonnet 4 | 0.590 | 0.865 | 0.948 |
| `gpt-51` | GPT-5 judge | 0.515 | 0.906 | 0.937 |

Claude remains systematically more generous on accuracy, while GPT-5 is somewhat more favorable to `gpt-51` on completeness. The mean absolute judge disagreement per meeting-model pair is:

| Model | Accuracy disagreement | Completeness disagreement | Coverage disagreement |
|---|---:|---:|---:|
| `gpt-41-mini` | 0.106 | 0.039 | 0.069 |
| `gpt-5-mini` | 0.122 | 0.033 | 0.058 |
| `gpt-51` | 0.141 | 0.044 | 0.018 |

The main systems implication is that accuracy remains the least stable metric across judges, while coverage is comparatively robust.

### 6.5 Error Structure

Persisted evaluator outputs make it possible to aggregate failure modes across the full benchmark.

| Issue type | Count across all inaccurate claims |
|---|---:|
| `unsupported_by_gt` | 6214 |
| `fabricated_facts` | 3293 |
| `factual_error` | 538 |
| `changed_certainty` | 131 |
| `contradicts_gt` | 114 |
| `changed_nature` | 113 |

For coverage, the dominant failure mode is:

| Issue type | Count across all uncovered GT items |
|---|---:|
| `missing` | 2198 |

These counts show that the benchmark is not mostly penalizing direct contradiction. The dominant accuracy failure is adding content unsupported by GT, whereas the dominant coverage failure is omission.

The same pattern appears in model-level counts aggregated at the meeting-model level.

| Model | Avg inaccurate claims / meeting-model pair | Avg total claims / meeting-model pair | Avg uncovered GT points / meeting-model pair | Avg GT points / meeting-model pair |
|---|---:|---:|---:|---:|
| `gpt-41-mini` | 12.05 | 28.16 | 5.29 | 26.52 |
| `gpt-5-mini` | 16.05 | 37.27 | 3.20 | 26.30 |
| `gpt-51` | 18.00 | 40.45 | 1.21 | 26.35 |

`gpt-41-mini` says less and therefore leaves more GT uncovered. `gpt-51` says the most and therefore leaves very little GT uncovered, but it also generates the largest number of unsupported or inaccurate claims. `gpt-5-mini` sits between these extremes, while `gpt-41-mini` retains the highest mean accuracy in the merged typed benchmark.

### 6.6 GT Validity Signals

The benchmark also exposes quality variation in the reference set. Within the merged typed benchmark, one meeting still contains a degenerate GT artifact with zero evaluable points (`t_258810779752442698698651215247285387144`), which propagates to six evaluator runs in the merged setting. That case contributes no meaningful factual comparison and should be interpreted as a benchmark-quality warning rather than as model behavior. We retain it for transparency, but it underlines a core system point: GT quality assurance is part of the evaluation problem, not a preprocessing footnote. A second, softer signal is the `whitehouse_press_briefings` normalization difference noted earlier: those GT files retain structured topics and points but omit stored metadata counters, so the evaluator reconstructs counts by traversing the GT structure at runtime. That difference does not invalidate the benchmark, but it shows that reference normalization itself is an evaluable systems concern.

## 7. Discussion

### 7.1 What the System Operationalizes

The central value of the benchmark is not simply that it assigns scores. It turns transcript-GT pairs into reusable model-selection evidence. Because the GT universe, prompt pipeline, and reporting schema are held fixed, changes in results are interpretable as changes in candidate behavior rather than as changes in the evaluation setup.

This is also the clearest distinction between the present work and a standalone factuality scorer. A scorer can estimate whether one summary is faithful. The system described here additionally supports repeated comparisons under a fixed protocol, release decisions, aggregate error mining, typed benchmark analysis, and identification of benchmark bottlenecks such as weak or degenerate GT.

The typed benchmark is especially important here. If the system reported only merged averages, the White House slice would appear merely as a moderate overall accuracy decline. The typed partition instead reveals a distinct failure regime: all three models retain high completeness and coverage there, but all three become much worse on accuracy because they introduce more unsupported specifics. This is a systems lesson rather than a purely statistical one. Typed benchmarks do not only improve reporting; they change what kinds of failures the organization can see at all.

The comparison with `private_data` and `city_council` makes that diagnosis sharper. Those two slices achieve much higher accuracy not because they use a different candidate-generation prompt, but because their GT artifacts are finer-grained and better aligned with the fact structure encouraged by the application-facing summary prompt. In `private_data`, GT points retain explicit owners, dependencies, timing, blockers, and action items. In `city_council`, GT points and decisions retain motions, dates, recommendations, procedural outcomes, and amounts. Quantitatively, the average claim-to-GT ratio is close to `1:1` in `private_data` (`1.05`) and `city_council` (`1.02`), but much higher in `whitehouse_press_briefings` (`1.41`). The average number of inaccurate claims per meeting-model pair follows the same pattern: `11.3` in `private_data`, `9.1` in `city_council`, and `20.38` in `whitehouse_press_briefings`.

This contrast suggests that the White House accuracy problem is not primarily a prompt-quality failure. The same prompt family produces acceptable accuracy on `private_data` and `city_council`, where GT is sufficiently claim-complete to absorb transcript-faithful detail. The harder White House regime emerges from a pipeline mismatch: the application-summary prompt produces detailed, transcript-faithful public-affairs summaries; claim extraction then atomizes those details into many candidate claims; and the coarser White House GT cannot support many of those specifics even when they are grounded in the transcript. The typed benchmark therefore reveals a systems diagnosis rather than a single-model defect. The dominant problem is misalignment among transcript structure, GT granularity, and evaluation resolution.

### 7.2 What Pipeline Reuse Buys Across Domains

The broader systems contribution is cross-domain reuse. The AI-search instantiation and the meeting-summary instantiation differ in task semantics, but they share the same evaluation architecture:

- curated reference artifacts
- controlled candidate outputs
- automated scoring
- persisted explanations
- report-backed comparison for release decisions

This means the repository is not a single-task benchmark script. It is an evaluation substrate that can support multiple AI products by swapping task-specific references and metrics while preserving the orchestration logic. In practical terms, the reuse boundary is concrete. The search and meeting-summary instantiations share artifact persistence, batch orchestration, judge aggregation, report generation, significance reporting, and release-facing comparison logic. The components that change are the semantic layers: the reference schema, the generation prompts, and the task-specific evaluators. The meeting-summary case further shows that this substrate remains useful when both reference generation and score generation are themselves structured. In roadmap terms, the same architecture supports benchmarking, regression detection, and failure-case analysis without rebuilding the full control plane for each product domain.

### 7.3 Implications for Model Selection

The benchmark supports a policy-driven interpretation. In the merged typed benchmark, `gpt-41-mini` has the highest mean accuracy, but the differences are not statistically significant. If the product objective is retention-first, `gpt-51` is preferable because its completeness and coverage advantages are both larger and statistically supported. If a deployment wants a single scalar ranking, the mean-of-metrics score favors `gpt-51`, but that choice should be made explicitly because it accepts lower accuracy in exchange for better retention.

This result is also useful as an engineering decision rule. “Not statistically significant” does not mean “irrelevant”; it means the benchmark does not support a stable accuracy winner under the present paired design. A disciplined release policy can therefore treat accuracy as a guardrail and tie-break signal, while reserving hard default-selection logic for metrics whose advantages are both large and significance-backed. In other words, the system helps separate what is directionally interesting from what is robust enough to gate releases.

### 7.4 Relationship to Claim-Based Evaluation Work

Relative to claim-based meeting-summary work, this paper shares the same factual core: summaries are judged against grounded factual units rather than only style or fluency. The difference is scope and structure. Most claim-based papers contribute a benchmark, a factuality metric, or an evaluator study. This paper contributes an implemented quality system around that core: structured GT construction, structured score generation, candidate generation, judge disagreement analysis, typed benchmark breakdowns, persisted reports, and release-facing comparison under a reusable cross-domain architecture. The same distinction also explains the architectural comparison in Table 0. General-purpose frameworks provide useful evaluation components, but this system treats reference construction, typed benchmarking, and report persistence as part of the evaluation product rather than as surrounding glue code.

### 7.5 Future Work and Improvement Plan

The White House anomaly points to a concrete improvement path. The first priority is **typed GT densification**. For briefing-style data, GT should preserve more of the entities, dates, quantities, organizations, and policy subclauses that are routinely expressed in transcript-faithful summaries. This is not only an annotation expansion step; it is a benchmark-quality intervention that reduces the gap between what the product-style prompt naturally summarizes and what the evaluator can legitimately score.

The second priority is **typed prompting rather than one-prompt-for-all evaluation**. The current benchmark intentionally fixes a single application-facing prompt family across all dataset types in order to isolate model effects. That choice is appropriate for comparison, but the typed results suggest that future production-oriented configurations should use prompt specializations by data regime. `private_data` and `city_council` benefit from prompts that foreground actions, owners, dates, and decisions. `whitehouse_press_briefings` likely needs a more conservative public-affairs variant that summarizes stance and topic structure without overcommitting to every policy qualifier or secondary numeric detail.

The third priority is to make the evaluator more explicit about **transcript-true but GT-omitted details**. At present, many such claims are absorbed into `unsupported_by_gt` or `fabricated_facts`, which is useful for conservative GT-based benchmarking but less useful for separating candidate error from GT incompleteness. A future score schema should therefore distinguish at least three conditions: genuinely inaccurate claims, GT-supported claims, and transcript-supported-but-GT-omitted claims. This would preserve strict benchmarking while improving diagnosis.

The fourth priority is deeper **structured candidate generation**. One reason this repository is reusable across domains is that both GT and score generation are structured. The same principle can be extended to candidates by introducing an intermediate structured summary ledger over entities, actions, decisions, dates, and quantities before the final natural-language rendering step. That intermediate representation would likely stabilize both summary generation and downstream claim extraction, especially in fact-dense slices such as `whitehouse_press_briefings`.

Finally, future work should validate improvements through **typed ablations rather than only merged reruns**. A practical next experiment is a 2 x 2 White House study: current GT vs denser GT, and current prompt vs a briefing-specialized prompt. Such a design would make it possible to attribute gains to benchmark improvement, prompt adaptation, or both. More broadly, the system should continue to use typed benchmarks as the control surface for quality iteration, because the central lesson of this paper is that merged averages alone hide diagnostically important failure regimes.

## 8. Limitations

### 8.1 GT Quality Bounds the Evaluation

If GT omits true details or compresses them inconsistently, some `unsupported_by_gt` findings may partly reflect reference limitations rather than pure candidate error. The current GT path relies on multi-stage model agreement and optional machine audit rather than mandatory human review, so the benchmark inherits the strengths and weaknesses of automated structured GT construction. The degenerate GT case in the benchmark makes this threat concrete.

### 8.2 LLM Judges Still Add Variance

Two judges improve robustness, but accuracy judgments remain somewhat unstable. Accuracy-sensitive release decisions should therefore consider both mean score and judge spread.

### 8.3 Internal Benchmark Slice

The 114-meeting merged typed benchmark is substantially stronger than a toy sample, but it still reflects the repository's current data mix. The results should be read as evidence about this system and these three meeting-data categories, not as universal conclusions about all meeting-summary tasks. The `private_data` subset contains only `22` meetings due to data-access constraints, which limits the statistical power of subset-level claims for that category; expanding that slice is an explicit target for future benchmark growth. The `whitehouse_press_briefings` slice behaves like a distinct sub-problem: the summaries become much less accurate there without a corresponding collapse in coverage or completeness. That makes the slice diagnostically valuable, but it also means the benchmark mixes multiple meeting-summary regimes rather than one homogeneous task.

### 8.4 Fixed Prompt Family

This study intentionally holds the summary prompt pipeline fixed at the current implementation (`standard_v1` + `format_v1`). The results therefore compare models under one prompt family rather than under each model's best possible prompt tuning.

### 8.5 Conservative Significance Test

The sign test fits the paired meeting-level comparison setting, but it ignores score magnitude. It therefore complements rather than replaces the descriptive mean differences reported earlier.

### 8.6 No Empirical Head-to-Head Against General-Purpose Evaluation Frameworks

Table 0 is architectural rather than empirical. A quantitative comparison with systems such as RAGAS, TruLens, or DeepEval on the same benchmark slice is left for future work. The present comparison is intentionally scoped to architecture and artifact design, because a fair head-to-head would require standardizing input formats, evaluator prompts, and aggregation semantics across systems.

### 8.7 No Benchmark-Wide Cost Table Yet

The repository records job duration and LLM token/latency telemetry, but those traces were not normalized into a complete benchmark-wide cost ledger for the historical runs used in this paper. The system is therefore instrumented for operational-cost reporting, but the present paper does not yet provide a complete per-stage latency/cost table.

## 9. Conclusion

We presented the Dataset Pipeline repository as a reusable cross-domain evaluation system whose current benchmarked instantiation targets AI meeting summaries and whose earlier instantiation supported AI search. On a merged typed benchmark of `114` meetings, `340` completed meeting-model pairs, and `680` evaluator runs, the system reveals a stable trade-off: `gpt-41-mini` is strongest on mean accuracy, whereas `gpt-51` is strongest on completeness and coverage. Paired sign tests show that the accuracy differences are not statistically significant after correction, while the retention advantages of `gpt-51` are significant.

Three broader conclusions follow. First, evaluation-pipeline reuse is practical across heterogeneous AI tasks when orchestration is separated from task-specific reference schemas and scoring layers. Second, the meeting-summary instantiation is strongest when both GT generation and score generation are structured, because that structure supports claim alignment, typed analysis, significance testing, and release-facing reporting. Third, typed benchmarks are diagnostic instruments rather than mere reporting conveniences: in this study they expose `whitehouse_press_briefings` as a distinct accuracy-hard regime driven mainly by unsupported additions under a coarser GT regime. More generally, the results show how pipeline-oriented evaluation can move from AI search to meeting summarization without changing its operational core, while leaving the online loop as a concrete next step for production-feedback integration.

## 10. Reproducibility Pointers

The full repository implementation underlying this paper is currently an internal Cisco repository. The files listed below are the packaged empirical basis for the reported results in this paper directory. To respect privacy constraints, the packaged `dataset/` subtree includes the `city_council` and `whitehouse_press_briefings` raw artifacts with their original repository paths preserved, but it intentionally excludes the raw `private_data` meeting contents. The combined benchmark CSVs are retained unchanged, so their aggregate statistics still reflect the full benchmark, including the private slice.

The main source artifacts for this paper are:

- [meeting-summary-system-paper.md](/Users/lizhon/PycharmProjects/WebexSuiteAI/dataset-pipeline/paper/meeting-summary-system-paper.md)
- [meeting_notes_model_comparison_combined_20260417.csv](/Users/lizhon/PycharmProjects/WebexSuiteAI/dataset-pipeline/paper/meeting_notes_model_comparison_combined_20260417.csv)
- [meeting_notes_model_comparison_combined_significance_20260417.csv](/Users/lizhon/PycharmProjects/WebexSuiteAI/dataset-pipeline/paper/meeting_notes_model_comparison_combined_significance_20260417.csv)
- [batch_meeting_notes_model_comparison.py](/Users/lizhon/PycharmProjects/WebexSuiteAI/dataset-pipeline/paper/batch_meeting_notes_model_comparison.py)
- [dual_loop_quality_framework.svg](/Users/lizhon/PycharmProjects/WebexSuiteAI/dataset-pipeline/paper/dual_loop_quality_framework.svg)
- [repository_pipeline_implementation.svg](/Users/lizhon/PycharmProjects/WebexSuiteAI/dataset-pipeline/paper/repository_pipeline_implementation.svg)
- [packaged dataset subtree](/Users/lizhon/PycharmProjects/WebexSuiteAI/dataset-pipeline/paper/dataset)

## References

Entries 1-10 are scholarly references. Entries 11-13 are software/documentation sources cited for the architectural capability comparison in Table 0.

1. Zhong, Philip, Kent Chen, and Don Wang. 2025. *Evaluating Embedding Models and Pipeline Optimization for AI Search Quality*. arXiv preprint arXiv:2511.22240. https://doi.org/10.48550/arXiv.2511.22240.
2. Janin, Adam, Don Baron, Jane Edwards, Dan Ellis, David Gelbart, Nelson Morgan, Barbara Peskin, Thilo Pfau, Elizabeth Shriberg, Andreas Stolcke, and Chuck Wooters. 2003. *The ICSI Meeting Corpus*. In *Proceedings of the IEEE International Conference on Acoustics, Speech, and Signal Processing (ICASSP 2003)*. https://catalog.ldc.upenn.edu/LDC2004S02.
3. McCowan, Iain, Jean Carletta, Wessel Kraaij, S. Ashby, Sandrine Bourban, Mike Flynn, Mathieu Guillemot, Thomas Hain, Jan Kadlec, Vasilis Karaiskos, Michael Kronenthal, Guillaume Lathoud, Mike Lincoln, Agnieszka Lisowska, Will Post, Dennis Reidsma, and Pete Wellner. 2005. *The AMI Meeting Corpus*. AMI Project research resource. https://research.utwente.nl/en/publications/the-ami-meeting-corpus.
4. Zhong, Ming, Da Yin, Tao Yu, Ahmed Hassan Awadallah, Xipeng Qiu, and Jiawei Han. 2021. QMSum: A New Benchmark for Query-Based Multi-Domain Meeting Summarization. In *Proceedings of the 2021 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies*. https://aclanthology.org/2021.naacl-main.472/.
5. Hu, Yue, Tzviya Ganter, Hanieh Deilamsalehy, Franck Dernoncourt, Hassan Foroosh, and Fei Liu. 2023. MeetingBank: A Benchmark Dataset for Meeting Summarization. In *Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)*. https://doi.org/10.18653/v1/2023.acl-long.906.
6. Kim, Soomin, Seongyun Weon, Jinhwi Kim, and Hyunjoong Ko. 2023. ExplainMeetSum: An Explainable Meeting Summarization Benchmark. In *Findings of the Association for Computational Linguistics: EMNLP 2023*. https://aclanthology.org/2023.findings-emnlp.573/.
7. Maynez, Joshua, Shashi Narayan, Bernd Bohnet, and Ryan McDonald. 2020. On Faithfulness and Factuality in Abstractive Summarization. In *Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics*, pages 1906–1919. Association for Computational Linguistics. https://aclanthology.org/2020.acl-main.173/.
8. Laban, Philippe, Tobias Schnabel, Paul N. Bennett, and Marti A. Hearst. 2022. SummaC: Re-Visiting NLI-Based Models for Inconsistency Detection in Summarization. *Transactions of the Association for Computational Linguistics* 10. https://doi.org/10.1162/tacl_a_00453.
9. Kiela, Douwe, Max Bartolo, Yixin Nie, Divyansh Kaushik, Atticus Geiger, Julian Michael, Niloofar Mireshghallah, Khyathi Chandu, Eric Wallace, Emily Dinan, Ashish Sabharwal, and Adina Williams. 2021. Dynabench: Rethinking Benchmarking in NLP. In *Proceedings of the 2021 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies*. https://www.research.ed.ac.uk/en/publications/dynabench-rethinking-benchmarking-in-nlp.
10. Es, Shahul, Jithin James, Luis Espinosa-Anke, and Steven Schockaert. 2023. RAGAs: Automated Evaluation of Retrieval Augmented Generation. arXiv preprint arXiv:2309.15217. https://arxiv.org/abs/2309.15217.
11. RAGAS Documentation. 2026. *Metrics Overview*. https://docs.ragas.io/en/stable/concepts/metrics/overview/. Accessed April 17, 2026.
12. TruLens Documentation. 2026. *Documentation Index*. https://www.trulens.org/docs/. Accessed April 17, 2026.
13. Confident AI Documentation. 2026. *LLM Evaluation Documentation*. https://www.confident-ai.com/docs. Accessed April 17, 2026.
