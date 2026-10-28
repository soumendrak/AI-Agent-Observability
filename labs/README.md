# Labs

Each lab has the same sections: goal, when it runs, steps, checkpoint, and what to do if you're stuck.

| Lab | When | File |
|---|---|---|
| 0. Setup (at home) | before the day | [00-setup](00-setup.md) |
| 1. First trace | Part 1 | [01-first-trace](01-first-trace.md) |
| 2. Read a trace | Part 2 | [02-read-a-trace](02-read-a-trace.md) |
| 3. The incident | Part 3 | [03-incident](03-incident.md) |
| 4. Fix and rerun | Part 3, after Lab 3 | [04-fix-and-rerun](04-fix-and-rerun.md) |
| 5. Build and test an evaluator | Part 4 | [05-evals](05-evals.md) |
| 6. Alerts (optional) | Part 5 | [06-alerts](06-alerts.md) |
| Worksheet | Labs 2 and 3 | [worksheet](worksheet.md) |

Working as a pair on one laptop is fine and encouraged. If the wifi or Langfuse is down, add `--exporter console` to any `ws run`, `ws case` or `ws load` command. You can still run the cases, read the trace tree in the terminal, and get the local check from `--rerun`. The Langfuse views, the evaluator and the alerts then become projector demos.
