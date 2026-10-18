# Maths appendix (Appendix B)

The workshop doesn't teach this part; it's here for Q&A and for afterwards. Unless a source is cited, the numbers are worked out here, and `tests/test_maths_appendix.py` recomputes every one of them.

## B0. Percentiles on small samples

For n = 50, the nearest-rank p99 is rank ceil(0.99 × 50) = 50, which is the maximum. numpy's default `method='linear'` puts p99 at 0-based position 0.99 × 49 = 48.51, 51% of the way from the second-largest value to the largest ([numpy.percentile](https://numpy.org/doc/stable/reference/generated/numpy.percentile.html)). The Langfuse pages we read don't say which method Langfuse uses. A p99 you can trust needs hundreds of runs, so use p50 and p95 for small samples. This appendix uses nearest rank, so you can check each value by hand.

## B1. Reliability compounding

These formulas assume the steps are independent and identical. Real agent steps are correlated: a slow provider or a cold cache slows several steps at once. Treat the numbers as intuition, not prediction.

Per-step success multiplies: 0.95^10 = 59.9% and 0.99^10 = 90.4%.

The chance that an n-step run hits at least one step's p99 is 1 − 0.99^n:

| n | 1 − 0.99^n |
|---|---|
| 5 | 4.9% |
| 10 | 9.6% |
| 25 | 22.2% |
| 50 | 39.5% |
| 100 | 63.4% |

[The Tail at Scale](https://cacm.acm.org/research/the-tail-at-scale/) reports 63% at fan-out 100.

## B2. Non-determinism: pass@k and pass^k

pass@k is the chance that at least one of k tries succeeds ([Chen et al. 2021](https://arxiv.org/abs/2107.03374)). pass^k is the chance that all k succeed ([τ-bench](https://arxiv.org/abs/2406.12045), which reports "pass^8 <25% in retail").

With p = 0.7: pass@3 = 1 − 0.3^3 = 97.3%, and pass^3 = 0.7^3 = 34.3%. Use pass^k for agents that act on behalf of users, because every customer gets one try.

## B3. Eval sample sizes and confidence intervals

95% Wilson intervals:

| Result | Interval |
|---|---|
| 9/10 | 59.6% to 98.2% |
| 45/50 | 78.6% to 95.7% |
| 450/500 | 87.1% to 92.3% |
| 44/50 vs 46/50 | 76.2% to 94.4% vs 81.2% to 96.8% |

To compare two rates, put an interval on the difference itself; don't check whether the two intervals overlap. For 44/50 vs 46/50 the gap is 4 points, with a 95% interval of −8.6 to +16.8 points (Newcombe's method, built from the two Wilson intervals). It includes 0, so 50 runs each can't tell these two apart.

Samples needed for a given margin at p = 0.5: about 384 for ±5 points, and about 1,067 for ±3.

Rule of three: 0 failures in n runs gives a 95% upper bound of about 3/n. So 0 failures in 50 runs still allows a failure rate of up to 6%.

## B4. Base rates and alert precision

Take an alert with 95% sensitivity and 95% specificity, when 2% of runs are bad. Its precision is 0.95 × 0.02 / (0.95 × 0.02 + 0.05 × 0.98) = 28%. At 1,000 runs a day, that's 19 true alarms and 49 false ones.

That's why you alert on windowed rates and read them next to the sample count. In Langfuse, a count alert flags a small sample but doesn't suppress the rate alert.

## B5. Burn rate

A 99% SLO leaves a 1% error budget. A burn rate of 14.4 spends 2% of a 30-day budget in 1 hour. The Google SRE workbook suggests paging at 2% in 1 hour or 5% in 6 hours, and opening a ticket at 10% in 3 days, with a short window checked at the same time ([SRE workbook](https://sre.google/workbook/alerting-on-slos/)).

Example rules: `chapters/ch11-alerting-slos/prometheus-alert-rules.yml` in [observability-engineering-series](https://github.com/soumendrak/observability-engineering-series).

## B6. Sampling and PII

Uniform 5% sampling keeps about 1 of 20 daily failures. Tail sampling keeps 100% of errors, 100% of slow runs and 5% of normal runs.

Redact prompts, emails and IDs before export, with the transform processor running before tail sampling. Example: `chapters/ch9-sampling-pii/otel-collector-config.yaml` in the same series.

## B7. Calibrating an LLM judge

Label 20 to 50 runs by hand, measure the judge's agreement with your labels, and fix the rubric before you trust its rate. Judges cost tokens on every scored observation. The workshop's judge prompt is in [evals/judge_prompt.md](../evals/judge_prompt.md).
