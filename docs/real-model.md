# Real-model demo (instructor)

The workshop labs use only the scripted fake model. This mode is for Soumen's short B8 demo: the same agent and the same trace tree, with a real model that answers differently each time.

1. Add these lines to `.env`. `OPENAI_BASE_URL` and `OPENAI_MODEL` are optional:
   ```
   LLM_MODE=openai
   OPENAI_API_KEY=sk-...
   OPENAI_BASE_URL=https://api.openai.com/v1
   OPENAI_MODEL=gpt-5.4-mini
   ```
   Any OpenAI-compatible provider works: set its `/v1` URL and model name. Without `OPENAI_BASE_URL` the OpenAI API is used. The default model is `gpt-5.4-mini`.
2. Run `uv run ws doctor`. The line `[OK] LLM_MODE=openai, model ... at ...` confirms the settings. The hello trace still uses the scripted model, so doctor spends no tokens.
3. Run the same request twice:
   ```
   uv run ws run "Book HYD to BLR on 2026-10-31"
   uv run ws run "Book HYD to BLR on 2026-10-31"
   ```
   Both traces have the same tree as the scripted run: root `tripmate`, `LangGraph`, then a generation, `search_flights`, a generation, `book_flight` and a final generation. The wording, timings and tokens differ.

Only `ws run`, `ws case 0` and `ws load --case 0` work in this mode. The workshop faults need the scripted model, so `ws case 1` and `ws case 2` stop with an error. Set `LLM_MODE=fake` again after the demo.
