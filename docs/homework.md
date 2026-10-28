# Homework

Do these after the workshop, in any order. They all use the same repo.

1. **Predict, then run.** Try Case 2 with other cities or dates. Before each run, write down what you expect the local check and the evaluator to say, then check:
   ```
   uv run ws case 2 "Book DEL to BOM on 2026-11-01" --rerun
   uv run ws case 2 "Book BOM to DEL on 2026-12-24" --rerun --guard off
   ```
   The flight data is in `src/tripmate/data/flights.json`. Pick routes from it, and also try one route that isn't in it.
2. **Token budget.** Set a budget of 3,000 tokens per run. Compare total tokens for `ws case 0` and the `ws case 2 --rerun` trace. Which one costs more, and why? Would a budget alert have fired?
3. **Your own agent.** Add the Langfuse `CallbackHandler` to an agent of your own. Wrap each run in a root observation that holds the structured request as input and the structured result as output, as `src/tripmate/agent.py` does. Then write one code evaluator for your most expensive mistake.
4. **The production checklist.** Go through [production-checklist.md](production-checklist.md) and mark which items your agent already does.
5. **The maths.** Read the [maths appendix](maths-appendix.md). Then work out the 95% interval for your own evaluator's pass rate on 20 runs.
