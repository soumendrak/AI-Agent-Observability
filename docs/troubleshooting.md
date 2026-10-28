# Troubleshooting

Find the message you see, then follow the fix. Run every command from the `AI-Agent-Observability` folder. Commands are the same in PowerShell and in macOS or Linux terminals unless a line says otherwise. Check before you install: run `uv --version` or `git --version` first, and install only if it fails. The README setup shows each install command for macOS, Windows and Linux.

Still stuck? Ask a TA, or post the exact message in the workshop chat. Never post your secret key. If you're offline or Langfuse is down, add `--exporter console` to any `ws run`, `ws case` or `ws load` command. The cases and the rerun check all work without a network.

## Installing

| You see | Fix |
|---|---|
| `uv: command not found` or `'uv' is not recognized` | Open a new terminal and run `uv --version` again. On Windows, close and reopen PowerShell. If it still fails, uv is missing: install it with the command for your system in README step 3, then open a new terminal. If it printed a version number, uv is installed, so do not install it again. |
| PowerShell refuses to run the uv installer | Use the exact installer line from the README; it includes `-ExecutionPolicy ByPass` for that one command. Or, only if `uv --version` fails, install with `winget install --id=astral-sh.uv -e`. |
| `uv sync` fails with a certificate or TLS error on a work laptop | The network inspects TLS. Try `uv sync --native-tls`, which uses the laptop's own certificate store (newer uv also calls it `--system-certs`). If it still fails, use a phone hotspot or pair with someone. |
| `git: command not found` or `'git' is not recognized` | Run `git --version`. If it fails, install git with the command for your system in README step 2, or from https://git-scm.com, then open a new terminal. If it printed a version number, git is installed, so do not install it again. |
| `fatal: destination path 'AI-Agent-Observability' already exists and is not an empty directory` | You already have the folder, so do not clone again. Run `cd ~/AI-Agent-Observability`, then `git pull --ff-only`. If `git -C AI-Agent-Observability rev-parse --is-inside-work-tree` says `not a git repository`, follow Case 3 in README step 5. It checks that the new folder name is free before it moves the old folder aside. |
| `Rename-Item` says `Cannot create a file when that file already exists` | A folder called `AI-Agent-Observability-old` is already there. Repeat the move in README step 5 with `AI-Agent-Observability-old2`. Check that name first with `Test-Path AI-Agent-Observability-old2`. It must print `False`. |
| `mv` printed nothing, but a folder named `AI-Agent-Observability` now sits inside `AI-Agent-Observability-old` | `AI-Agent-Observability-old` was already there, so `mv` put the folder inside it. Nothing was deleted. Ask a TA, or post what `ls AI-Agent-Observability-old` prints in the workshop chat. Next time, run the name check in README step 5 before `mv`. |
| `git pull --ff-only` says your local changes would be overwritten | Run `git stash push --include-untracked -m "before-workshop"`, then `git pull --ff-only` again. |
| `git pull --ff-only` says `You are not currently on a branch` | You are on the fixed workshop version. Run `git checkout main`, then `git pull --ff-only`. If `git checkout main` complains about local changes, run `git stash push --include-untracked -m "before-workshop"` first, then `git checkout main`, then `git pull --ff-only`. |
| `git pull --ff-only` says `fatal: Not possible to fast-forward, aborting.` | Your copy has a change that the workshop copy does not, so git refuses to merge it for you. Nothing was changed and your files are safe. Ask a TA, or post the exact message in the workshop chat. Ignore git's hints about merge and rebase. If you only want a clean copy, follow Case 3 in README step 5 to move the folder aside and clone again. Your old folder, with your `.env`, stays in place. |
| `Failed to spawn: ws` from uv | You're not in the repo folder, or `uv sync` didn't finish. `cd AI-Agent-Observability`, run `uv sync`, then try again. |

## `uv run ws doctor`

Doctor stops at the first `[FAIL]`, and each message names its fix. `[WARN]` lines don't stop it, and you still get READY.

| You see | What it means and how to fix it |
|---|---|
| `[FAIL] Python 3.11 is running` | Something other than uv started Python. Run `uv sync`, then `uv run ws doctor`. Always start commands with `uv run`. |
| `[FAIL] no .env here; copy .env.example to .env in the repo folder` | Check you're in the repo folder, then check for the file first. macOS or Linux: `ls .env`. PowerShell: `Test-Path .env`. If `ls` says `No such file or directory`, or PowerShell says `False`, copy the example. macOS or Linux: `cp .env.example .env`. PowerShell: `Copy-Item .env.example .env`. If the file is already there, do not copy over it, because that erases your keys. Open it and fix the values instead. |
| `[FAIL] .env is not UTF-8 text; open it in an editor and save it as UTF-8` | The editor saved `.env` in an older encoding. Open it in VS Code or Notepad, choose Save As, pick UTF-8, and save. Files that Windows PowerShell 5 writes as UTF-16 are read automatically, so only other encodings get this message. |
| `[FAIL] the keys are swapped; LANGFUSE_PUBLIC_KEY starts with pk-lf-` | Swap the two values in `.env`. The public key starts with `pk-lf-` and the secret key with `sk-lf-`. |
| `[FAIL] paste your project's keys into .env (pk-lf-... and sk-lf-...)` | `.env` still has the placeholders from `.env.example`. In Langfuse, open the project settings, create an API key pair, and paste both values. |
| `[FAIL] set LANGFUSE_BASE_URL to your region` | The URL is missing or isn't a URL. Use `https://cloud.langfuse.com` (EU) or `https://us.cloud.langfuse.com` (US), the region where you created the account. |
| `[FAIL] LANGFUSE_BASE_URL must stop after the host` | You pasted a link from the browser. Keep only the start, for example `https://us.cloud.langfuse.com`, and delete the `/project/...` part. |
| `[FAIL] LLM_MODE=... is not supported; set LLM_MODE=fake in .env` | The labs use only the scripted model. Set `LLM_MODE=fake`. `LLM_MODE=openai` is for the instructor demo in [real-model.md](real-model.md). |
| `[FAIL] LLM_MODE=openai needs the openai extra; run: uv sync --extra openai` | The real-model demo needs packages that the plain `uv sync` leaves out. Run `uv sync --extra openai`, or set `LLM_MODE=fake`. |
| `[FAIL] these keys belong to the US region: set LANGFUSE_BASE_URL=https://us.cloud.langfuse.com in .env` | Wrong region. Doctor tried your keys in the other region and they work there. Change `LANGFUSE_BASE_URL` as the message says. |
| `[FAIL] Langfuse at https://cloud.langfuse.com rejected the keys (HTTP 401)` | The keys don't work in this region, and doctor couldn't confirm them in the other one. Check you picked the region where you created the account. Then copy the keys again from the project settings (no spaces or quotes), or create a new key pair. |
| `[FAIL] cannot reach https://cloud.langfuse.com (ConnectError)` | No connection to Langfuse. Check the wifi. On a work laptop, a proxy, VPN or TLS inspection can block it, so try a hotspot. In the room, carry on with `--exporter console`. |
| `[FAIL] Langfuse at https://cloud.langfuse.com answered HTTP 503` | Langfuse is busy or down; your setup is fine. Try again later. Check https://status.langfuse.com. |
| `[FAIL] the hello trace has not shown up in Langfuse after 30 s` | Ingestion is slow right now. Run `uv run ws doctor` again later. |
| `[WARN] guards.py differs from the workshop version` | You edited `src/tripmate/guards.py`. That's expected during Lab 4. Before the workshop, set it aside with `git stash push --include-untracked -m "before-workshop"`. |
| `[WARN] not on the workshop version v2026.10.31` | Switch to the final version with the 4 commands from the email: `git fetch --tags`, then `git stash push --include-untracked -m "before-workshop"`, then `git checkout v2026.10.31`, then `uv sync`. Git's note about "detached HEAD" is expected. |
| `[WARN] v2026.10.31 isn't in this clone yet` | Your clone hasn't fetched the final version, or it isn't published yet. Run `git fetch --tags`, then `git tag -l v2026.10.31`. If it lists the tag, run the four commands above. If not, the tag isn't out yet: carry on and run `uv run ws doctor` again later. |
| `[WARN] this folder is not a git clone` | You downloaded a zip. Clone instead, so the final-version steps work. First check for an existing clone with `git -C AI-Agent-Observability rev-parse --is-inside-work-tree`. If it says `true`, use that folder. If it does not, move the zip folder aside as in the row above, then run `git clone https://github.com/soumendrak/AI-Agent-Observability`. |
| `[WARN] git was not found` | Run `git --version`. If it fails, install git (README step 2), so doctor can check `guards.py` and the version. |
| `[WARN] git won't read this folder because another user owns it` | The folder was created by another user account (common on shared or copied drives). Run the `git config --global --add safe.directory ...` command the message shows. |
| `[WARN] git did not answer` | git hung or couldn't start. Run `uv run ws doctor` again; if it repeats, check that `git status` works in this folder. |

## Running a case

| You see | Fix |
|---|---|
| `error: missing LANGFUSE_PUBLIC_KEY...` | There's no `.env` in this folder, or it lacks the keys. Copy `.env.example` to `.env` in the repo folder and fill it in (see the README setup), or add `--exporter console` to work offline. |
| `trace: unavailable (UnauthorizedError), check the keys and LANGFUSE_BASE_URL in .env` | The run worked but the trace link couldn't be built. Run `uv run ws doctor` to find out why. |
| `error: could not read the trip from` | `ws run` takes a request like `"Book HYD to BLR on 2026-10-31"`: three-letter airport codes, the word `to`, and a date. Put the request in quotes. |
| `error: --score sdk sends scores to Langfuse; drop --exporter console` | `--score sdk` needs Langfuse, so it doesn't work offline. Use one or the other. |
| The trace link opens a login page or "not found" | Log in to the same Langfuse account and region as your keys. |

## Lab 4: your `guards.py` edit

`uv run ws case 2 --rerun` reloads `src/tripmate/guards.py` every time. You don't need to restart anything, just save the file.

| You see | Fix |
|---|---|
| `error: guards.py line 3:` followed by a Python message | A syntax error on that line. Check the indentation (4 spaces), colons at the end of `if` lines, and matching quotes and brackets. |
| `error: guards.py could not be loaded: NameError` | The file runs into a problem before the function is even called, often a typo outside the function or an import that doesn't exist. Read the message after the colon. |
| `error: guards.py must define validate_booking(requested, args)` | The function was renamed or deleted. Keep the name and the two parameters exactly as shipped. |
| `guard: error in guards.py` followed by, for example, `AttributeError: 'dict' object has no attribute 'origin'` | Your function crashed instead of deciding. `requested` and `args` are dictionaries, so write `args["origin"]`, not `args.origin`. Then rerun. Until the guard runs cleanly, the last line says `booking_matches_request: not checked; fix the error in guards.py first`. |
| `guard: no-op` | The wrong booking went through, so your guard didn't reject it. Check that you saved the file, that you compare all three fields, and that a mismatch raises an error. A failed `assert` also counts as a rejection. |

## In the Langfuse UI

| You see | Fix |
|---|---|
| The evaluator test says `missing field: requested.origin` | You tested the wrong observation or an old trace. Pick the root observation named `tripmate` from a fresh run. |
| Your own script gets HTTP 410 `LEGACY_API_UNAVAILABLE_FOR_NEW_ORGANIZATION` | Your organization can't use the deprecated read APIs (`/api/public/traces`, `/api/public/observations`, `/api/public/scores`); Langfuse Cloud removes them for everyone on 16 Nov 2026 ([compatibility](https://langfuse.com/docs/compatibility)). Read observations with `GET /api/public/v2/observations?fields=core,basic,io` (without `io` there's no `input` or `output`) and scores with `GET /api/public/v3/scores`. In v2, `input` and `output` come back as JSON strings, so parse them first. The workshop commands don't use the old APIs. |
| An alert shows `NO_DATA` | Nothing matched in the window: no scores yet, nobody ran the agent, or the score name is wrong. Compare with the count of `tripmate` traces in the same window. |
