# Production checklist

What to take from the workshop to your own agent. Each item points back to what you did with TripMate.

1. **Trace every LLM call and tool call** with OpenTelemetry-based instrumentation. Prefer the OTel GenAI attribute names where your backend maps them. *(TripMate: the Langfuse SDK and its LangChain `CallbackHandler`.)*
2. **Put the structured request and the tool's structured result on the root span.** Never treat LLM text as the record of what happened. *(The root `tripmate` carries `input.requested` and `output.booking`.)*
3. **Validate tool arguments against the request before any action that changes something**: a booking, a payment, a delete. *(Lab 4, `validate_booking` in `guards.py`.)*
4. **Set the span status to ERROR and record the exception**, even when the agent recovers. *(The red `book_flight` span in Case 1 and in the guarded rerun.)*
5. **Propagate session, user and release IDs** to every span, so you can slice by customer and by deploy.
6. **Cap steps and retries, and record when the cap is hit.** *(TripMate stops after 8 model steps.)*
7. **Track p50, p95 and p99 latency, the tool error rate, and tokens and cost per run.** Never track only the mean. *(Lab 2: one slow run moves the mean, not the median.)*
8. **Run a structured code eval on live traffic for your most expensive mistake.** *(Lab 5, `booking_matches_request` on every root `tripmate`.)*
9. **Calibrate any LLM judge against human labels before you alert on it.** Label 20 to 50 runs by hand and measure agreement first.
10. **Alert on rates over windows, with explicit no-data handling.** Use NO_DATA, with a notification if it lasts. NO_DATA means no matching data in the window. A broken evaluator causes it, but so does no traffic or a wrong filter, so check the request volume first. A low-count alert doesn't suppress the rate alert. It only flags that the rate rests on a small sample. *(Lab 6.)*
11. **Tail-sample:** keep every error and every slow run, and only a sample of the normal ones.
12. **Redact PII before export, and keep keys out of traces.** Rotate any key that was ever shown on screen.

More detail on the numbers behind items 7, 9, 10 and 11 is in the [maths appendix](maths-appendix.md).
