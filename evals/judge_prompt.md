# LLM-as-a-Judge prompt: does the booking match the request?

This is Soumen's demo in block B26, run in his own Langfuse project. You don't need it for the labs. A judge needs an LLM Connection, which means a provider key, and it costs tokens on every observation it scores. The code evaluator in `booking_matches.py` checks the same thing for free and gives the same answer every time.

## Set it up in Langfuse

1. Settings > LLM Connections: add a provider key. The model must support structured output.
2. Evaluators > New evaluator > LLM-as-a-Judge, blank prompt.
3. Paste the two messages below. Use a **System** message for the first and a **User** message for the second.
4. Score type: **Boolean**. Score name: `booking_matches_request_judge`, so it doesn't mix with the code evaluator's `booking_matches_request`.
5. Map the variables: `{{input}}` is the observation's input and `{{output}}` is its output.
6. Test it on root `tripmate` observations from `ws case 0`, `ws case 2` and the `ws case 2 --rerun` trace. Then save with a rule: Is Root Observation = true, name = `tripmate`, new data only.

## System message

```
You are a strict auditor for a travel-booking agent. You compare facts, not wording.

The input is JSON. Its "requested" object holds what the customer asked for: origin, destination and date.
The output is JSON. Its "booking" object holds what the booking tool actually booked. Its "final_message" is what the agent told the customer.

Rules:
- Judge only "requested" against "booking". Ignore "final_message" when deciding: it is the agent's claim, not a record of what happened.
- Compare origin with origin, destination with destination, and date with date. Ignore spaces around a value, and airport codes are case-insensitive.
- If "booking" is missing, or any of the three fields is missing on either side, the answer is false.
- Each airport code must be exactly three letters A to Z, such as HYD. Anything else, such as HYDE or H1D, is invalid.
- Each date must be a real calendar date written YYYY-MM-DD, such as 2026-10-31. Anything else, such as 2026-02-30 or 2026/10/31, is invalid.
- If any value on either side is invalid, the answer is false, even when both sides hold the same invalid value.
- The answer is true only if all three fields are valid and match.
```

## User message

```
Input:
{{input}}

Output:
{{output}}

Does the booking match the request? Answer true or false. In the reasoning, name each field that differs, with the requested and booked values, or say "all fields match".
```

## What to say about it

- Compare it with the code evaluator on the same traces. They should agree on Cases 0 and 2 and on the rerun. Point out any disagreement, because that's what calibration is for (Appendix B7 in [maths-appendix.md](../docs/maths-appendix.md)).
- Cost: one judge call per scored observation. The code evaluator costs nothing and doesn't vary from run to run.
- Use code evaluators for facts like these, and judges for semantics, such as whether the confirmation was polite or clear.
