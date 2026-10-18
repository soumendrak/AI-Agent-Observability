# AI Agent Observability

Code for the hands-on workshop **Zero to Hero on AI Agent Observability** (The Data AI Guild, Hyderabad, Saturday 31 October 2026).

You run TripMate, a small travel-booking agent, on your laptop. It sends its traces to your own free Langfuse account. During the workshop you find out why it booked the wrong flight, fix it, and prove the fix with an evaluator. The agent uses a scripted fake model, so you need no LLM key and every laptop sees the same thing. All data is made up.

**You can pair.** Two people on one laptop is fine and often more fun. One of you does this setup, and you sit together on the day.

## Setup (about 15 minutes)

You need a laptop you can install software on, git, and a network connection. uv installs Python 3.12 for you.

1. **Langfuse account.** Sign up free at https://cloud.langfuse.com (EU) or https://us.cloud.langfuse.com (US); no credit card needed. Create an organization and a project called `tripmate-workshop`. In the project settings, create an API key pair. Note the region you picked.

2. **Install uv.**

   macOS or Linux:
   ```
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   Windows (PowerShell):
   ```
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
   Open a new terminal afterwards so `uv` is on your PATH.

3. **Get the code.**
   ```
   git clone https://github.com/soumendrak/AI-Agent-Observability
   cd AI-Agent-Observability
   uv sync
   ```

4. **Add your keys.** Copy the example file:

   macOS or Linux: `cp .env.example .env`
   Windows (PowerShell): `Copy-Item .env.example .env`

   Open `.env` in any editor and fill in your public key (`pk-lf-...`), secret key (`sk-lf-...`) and `LANGFUSE_BASE_URL`: `https://cloud.langfuse.com` for EU or `https://us.cloud.langfuse.com` for US. Leave `LLM_MODE=fake` as it is.

5. **Check it.**
   ```
   uv run ws doctor
   ```
   Each check prints `[OK]`. A `[WARN]` line is advice and doesn't stop the checks: you still get READY. The last lines are a link to a test trace and a code like `READY-7F3A`. Open the link to see your trace, then submit the code on the form from the setup email.

   If a line says `[FAIL]`, it names the cause and the fix. If you're still stuck, post the exact message in the workshop chat. Never post your secret key.

## Common errors

`ws doctor` stops at the first `[FAIL]` and prints a one-line cause and fix. `[WARN]` lines don't stop it. The `error:` and `guard:` lines come from `ws run` and `ws case`. The usual ones:

| You see | Fix |
|---|---|
| `[FAIL] no .env here; copy .env.example to .env in the repo folder` | Run the copy command from step 4 inside the repo folder |
| `error: missing LANGFUSE_PUBLIC_KEY...` | Same cause from `ws run` or `ws case`: create `.env` as in step 4, or add `--exporter console` |
| `[FAIL] paste your project's keys into .env (pk-lf-... and sk-lf-...)` | Replace the placeholders with your project's API keys |
| `[FAIL] the keys are swapped; LANGFUSE_PUBLIC_KEY starts with pk-lf-` | Swap the two key values in `.env` |
| `[FAIL] these keys belong to the US region: set LANGFUSE_BASE_URL=https://us.cloud.langfuse.com in .env` | Wrong region: set the URL the message names |
| `[FAIL] LANGFUSE_BASE_URL must stop after the host` | Keep only `https://cloud.langfuse.com` or `https://us.cloud.langfuse.com`, without `/project/...` |
| `[FAIL] Langfuse at https://cloud.langfuse.com rejected the keys (HTTP 401)` | Copy both keys again from the project settings, or create a new pair |
| `[FAIL] .env is not UTF-8 text; open it in an editor and save it as UTF-8` | Save `.env` as UTF-8 (UTF-16 from PowerShell is read automatically) |
| `[FAIL] cannot reach https://cloud.langfuse.com (ConnectError)` | Check the wifi, proxy or VPN; try a hotspot, or work offline with `--exporter console` |
| `[WARN] guards.py differs from the workshop version` | Before the workshop: `git stash push --include-untracked -m "before-workshop"` |
| `[WARN] not on the workshop version v2026.10.31` | `git stash push --include-untracked -m "before-workshop"`, then `git fetch --tags`, then `git checkout v2026.10.31`, then `uv sync` |
| `guard: error in guards.py` | Your Lab 4 edit crashed; the message names the Python error. Use `args["origin"]`, not `args.origin` |

Every message, with more detail, is in [docs/troubleshooting.md](docs/troubleshooting.md).

## Commands

All commands run from the repo folder, and work the same in PowerShell and in macOS or Linux terminals.

| Command | What it does |
|---|---|
| `uv run ws doctor` | Checks your setup, sends a test trace, prints your READY code |
| `uv run ws run "Book HYD to BLR on 2026-10-31"` | Runs TripMate on your own request and prints the trace link |
| `uv run ws case 1` | Runs a workshop case; the labs tell you which one |
| `uv run ws case 2 --rerun` | Reloads your `guards.py` edit, reruns, and checks the result locally |
| `uv run ws load -n 50` | Runs a case many times, for latency percentiles and scores |
| `uv run ws case 0 --exporter console` | Works offline: prints the trace as a tree in the terminal, sends nothing |

`--exporter console` works with every command except `doctor`. Use it if the wifi or Langfuse is down; the cases and the rerun check all work offline.

## Before the workshop

You'll edit one function in `src/tripmate/guards.py` during the workshop. Any editor works. Please don't edit it before the day. If you already did, `uv run ws doctor` warns you, and the final email tells you how to set it aside.

On Friday 30 October you'll get the exact commands to switch to the final version.

## Privacy

The workshop uses only made-up data. Keep your keys in `.env`, which git ignores. Never share your secret key in chat or on screen. If it leaks, rotate it in the Langfuse project settings.
