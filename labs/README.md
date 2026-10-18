# Labs

Each lab has the same sections: goal, when it runs, steps, checkpoint, and what to do if you're stuck. Lines starting with **Soumen:** are placeholders for the guide text and screenshots. They're written on Fri 23 Oct, against the merged build.

| Lab | Workshop time | File |
|---|---|---|
| 0. Setup (at home) | before the day | [00-setup](00-setup.md) |
| 1. First trace | 00:10 to 00:20 | [01-first-trace](01-first-trace.md) |
| 2. Read a trace | 00:20 to 00:45 | [02-read-a-trace](02-read-a-trace.md) |
| 3. The incident | 00:45 to 01:15 | [03-incident](03-incident.md) |
| 4. Fix and rerun | 01:15 to 01:25 | [04-fix-and-rerun](04-fix-and-rerun.md) |
| 5. Build and test an evaluator | 01:40 to 02:15 | [05-evals](05-evals.md) |
| 6. Alerts (optional) | 02:20 to 02:40 | [06-alerts](06-alerts.md) |
| Worksheet | Labs 2 and 3 | [worksheet](worksheet.md) |

Working as a pair on one laptop is fine and encouraged. If the wifi or Langfuse is down, add `--exporter console` to any `ws run`, `ws case` or `ws load` command. You can still run the cases, read the trace tree in the terminal, and get the local check from `--rerun`. The Langfuse views, the evaluator and the alerts then become projector demos.
