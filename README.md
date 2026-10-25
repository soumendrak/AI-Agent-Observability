# AI Agent Observability

Code for the hands-on workshop **Zero to Hero on AI Agent Observability** (The Data AI Guild, Hyderabad, Saturday 31 October 2026).

This page is a step-by-step guide. It assumes you have never used Git, a terminal or Langfuse. Follow the steps in order and run every command exactly as written.

**You can pair.** Two people on one laptop is fine and often more fun. One of you does this setup, and you sit together on the day.

## What you will build

You run TripMate, a small travel-booking agent, on your laptop. It sends its traces to your own free Langfuse account. During the workshop you do five things:

1. Run the agent and see its first trace.
2. Read a trace and measure how long runs take.
3. Find out why the agent booked the wrong flight.
4. Fix the agent and prove the fix with an evaluator.
5. Set up an alert that tells you when it happens again.

The agent uses a scripted fake model, so you need no LLM key and every laptop sees the same thing. All data is made up.

## Before the day, checklist

Finish this list at home. It takes about 15 minutes.

- [ ] A laptop you can install software on. Not a locked work laptop.
- [ ] A working internet connection.
- [ ] A free Langfuse account and a project with API keys (Setup, step 4).
- [ ] Git installed (Setup, step 2).
- [ ] uv installed (Setup, step 3).
- [ ] The code on your laptop (Setup, step 5).
- [ ] A `.env` file with your keys (Setup, step 6).
- [ ] `uv run ws doctor` ends with a `READY-` code (Setup, step 8).
- [ ] Your READY code submitted on the form from the setup email.
- [ ] A text editor. Notepad, TextEdit and nano all work.
- [ ] Your charger.

If a step fails, go to [Common errors](#common-errors). Do not skip a failed step.

## Words you will see

| Word | What it means |
|---|---|
| Terminal | A window where you type commands and press Enter. |
| Repo | Short for repository. A folder of code that Git tracks. |
| Git | A tool that copies and tracks code. You use it once, to download this repo. |
| Clone | Download a repo to your laptop with `git clone`. |
| uv | A tool that installs Python and the packages this repo needs. |
| Virtual environment | A private folder (`.venv`) that holds this repo's Python and packages. `uv` creates it for you. |
| `.env` | A plain text file in the repo folder that holds your Langfuse keys. Git ignores it. |
| API key | A password that lets a program use your Langfuse account. You get a pair, a public key and a secret key. |
| Trace | The full record of one agent run, from the request to the answer. |
| Span | One step inside a trace, such as a model call or a tool call. Langfuse also calls it an observation. |
| Evaluator | A small program that reads a trace and gives it a score. |
| Guard | A check in `guards.py` that stops a bad tool call. You write one in Lab 4. |

## Setup (about 15 minutes)

You need a laptop you can install software on, a network connection and a Langfuse account. uv installs Python 3.12 for you. You do not install Python yourself.

Every command in this guide goes in a terminal. Type it, or copy and paste it, then press Enter. Run one command at a time. Wait for it to finish before you run the next.

### Step 1. Open a terminal

macOS:

1. Press Cmd and Space together.
2. Type `Terminal`.
3. Press Enter.

Windows:

1. Click the Start menu.
2. Type `PowerShell`.
3. Click **Windows PowerShell**. Do not pick the one that says ISE.

Linux:

1. Press Ctrl, Alt and T together. If nothing opens, find **Terminal** in your app menu.

You see a window with a line of text that ends in `$`, `%` or `>`. That is the prompt. You type after it.

Move to your home folder. Every machine understands this command.

```
cd ~
```

Check where you are.

```
pwd
```

It prints a folder path that holds your user name, such as `/Users/asha` on macOS, `/home/asha` on Linux or `C:\Users\asha` on Windows. Do not use a folder that OneDrive, iCloud or Dropbox syncs.

### Step 2. Install Git

Check whether you already have it.

```
git --version
```

If a line starting with `git version` appears, go to step 3. The number after it can differ from anyone else's. That is fine.

If you see an error such as `command not found` or `not recognized`, install Git.

macOS. Run this, click **Install** in the window that opens, then wait.

```
xcode-select --install
```

Windows. Run this, then close PowerShell and open a new one.

```
winget install --id Git.Git -e --source winget
```

If `winget` is not found, download the installer from https://git-scm.com/download/win, run it and accept every default.

Linux on Debian or Ubuntu.

```
sudo apt-get install git
```

Linux on Fedora.

```
sudo dnf install git
```

Run `git --version` again. It must print a line starting with `git version`.

### Step 3. Install uv

macOS or Linux.

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows (PowerShell). Copy the whole line.

```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

The installer prints several lines and ends with `everything's installed!`.

Now close the terminal and open a new one, as in step 1. A terminal that was open during the install does not know about `uv` yet. Then move back to your home folder.

```
cd ~
```

Check uv.

```
uv --version
```

It prints `uv` and a version number. If it says `command not found` or `not recognized`, read [Windows traps](#windows-traps) or [docs/troubleshooting.md](docs/troubleshooting.md).

### Step 4. Make a Langfuse account and keys

Do this in your web browser.

1. Go to https://cloud.langfuse.com for the EU region or https://us.cloud.langfuse.com for the US region. Pick one and remember it. You need no credit card.
2. Sign up and create an organization.
3. Create a project called `tripmate-workshop`.
4. Open the project **Settings** and find **API Keys**.
5. Create a new key pair. If the form asks what the key may do, choose full access, because `ws doctor` reads data back.
6. Copy both keys into a scratch note. The public key starts with `pk-lf-`. The secret key starts with `sk-lf-`.

Langfuse shows the secret key only once. If you lose it, create a new key pair and delete the old one. Read [Never share your secret key](#never-share-your-secret-key) before you go on.

### Step 5. Download the code

```
git clone https://github.com/soumendrak/AI-Agent-Observability
```

It prints `Cloning into 'AI-Agent-Observability'...` and then a few progress lines.

Go into the new folder.

```
cd AI-Agent-Observability
```

From now on, every command runs in this folder. Check you are in it.

```
pwd
```

The path must end with `AI-Agent-Observability`. If it does not, run `cd ~/AI-Agent-Observability`.

Install everything the repo needs.

```
uv sync
```

It can take a minute or two on slow wifi. It prints `Using CPython 3.12`, then `Creating virtual environment at: .venv`, then a long list of lines that start with `+`. It ends with no error.

### Step 6. Add your keys to `.env`

Copy the example file. The copy is your private `.env` file.

macOS or Linux.

```
cp .env.example .env
```

Windows (PowerShell).

```
Copy-Item .env.example .env
```

The command prints nothing when it works. Files that start with a dot are hidden. To see yours, list all files.

macOS or Linux.

```
ls -a
```

Windows (PowerShell).

```
ls -Force
```

You see `.env` and `.env.example` in the list.

Open `.env` in an editor.

macOS.

```
open -e .env
```

Windows (PowerShell).

```
notepad .env
```

Linux.

```
nano .env
```

If you installed VS Code, `code .env` works on all three systems.

You see four lines. Change the first three so they look like this, with your own keys.

```
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key-here
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key-here
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

Follow these rules.

- No spaces around the `=`.
- No quotes around the values.
- Use `https://cloud.langfuse.com` for the EU region. Use `https://us.cloud.langfuse.com` for the US region.
- Leave the line `LLM_MODE=fake` as it is.

Save the file. In TextEdit use Cmd and S. If TextEdit shows rich text, choose **Format** then **Make Plain Text** first. In Notepad use Ctrl and S. In nano press Ctrl and O, then Enter, then Ctrl and X.

### Step 7. Check the install without Langfuse

This step proves the code runs on your laptop. It sends nothing to Langfuse.

```
uv run ws case 0 --exporter console
```

You see the trace as a tree in your terminal. It looks like this.

```
agent tripmate OK
    requested: {"origin": "HYD", "destination": "BLR", "date": "2026-10-31"}
    booking: {"pnr": "DE224B", "flight": "TM-204", "origin": "HYD", "destination": "BLR", "date": "2026-10-31"}
    final_message: "Booked TM-204 HYD to BLR on 2026-10-31. PNR DE224B."
  chain LangGraph OK
    agent agent OK
      generation ScriptedFakeLLM OK
      chain tools_condition OK
    chain tools OK
      tool search_flights OK
          args: {"origin": "HYD", "destination": "BLR", "date": "2026-10-31"}
    agent agent OK
      generation ScriptedFakeLLM OK
      chain tools_condition OK
    chain tools OK
      tool book_flight OK
          args: {"origin": "HYD", "destination": "BLR", "date": "2026-10-31"}
    agent agent OK
      generation ScriptedFakeLLM OK
      chain tools_condition OK
TripMate: Booked TM-204 HYD to BLR on 2026-10-31. PNR DE224B.
trace: offline (--exporter console), nothing was sent to Langfuse
```

Read it from the top. The first line is the whole run. Each indented line is a span inside it. The words `generation` and `tool` tell you what kind of step it was. `OK` means the step worked.

If this fails, the install is the problem and your keys are not. Run `uv sync` again and check that `pwd` ends with `AI-Agent-Observability`.

### Step 8. Run doctor

```
uv run ws doctor
```

Doctor checks your setup one line at a time. It stops at the first `[FAIL]` line. A `[WARN]` line is advice and does not stop it.

If your keys are right, every check prints `[OK]`. The checks cover your Python version, the `.env` file, the shape of your keys, `LLM_MODE=fake` and a real call to your Langfuse project. The last two lines are the link to a test trace and a code such as `READY-7F3A`. Your code differs. It comes from your project.

1. Click or copy the line that starts with `hello trace:` and open the link in your browser. You see the test trace that doctor just sent. If you cannot click the link, copy it into the address bar.
2. Copy your `READY-` code.
3. Paste it into the form from the setup email.

Doctor never prints your keys, so you can paste its output into the workshop chat.

Do you see a `[FAIL]` line instead? Doctor names the cause and the fix. For a missing `.env` it prints this.

```
[OK] Python 3.12
[FAIL] no .env here; copy .env.example to .env in the repo folder
```

If you copied the example file and did not paste your keys yet, it prints this.

```
[OK] Python 3.12
[OK] .env found
[FAIL] paste your project's keys into .env (pk-lf-... and sk-lf-...)
```

Fix the line that doctor names, then run `uv run ws doctor` again. Find your message in [Common errors](#common-errors). You are done with setup when you see `READY-`.

## The day, lab by lab

Open your terminal on the day and move into the repo.

```
cd ~/AI-Agent-Observability
```

Keep two things open. One is the terminal. The other is your Langfuse project in the browser. In Langfuse, click **Tracing** in the left menu to see your traces.

The guide below follows the workshop slides. Times are the slide times, counted from the start of the session. The labs run in windows that end on a checkpoint, not on the clock. Put a green sticky on your laptop when you are ready and a red one when you need help. TAs go to the red ones.

| Part | Time | Lab |
|---|---|---|
| 1. Opening and first trace | 00:00 to 00:16 | [Lab 1](labs/01-first-trace.md) |
| 2. Read a trace | 00:16 to 00:41 | [Lab 2](labs/02-read-a-trace.md) |
| 3. The incident | 00:41 to 01:21 | [Lab 3](labs/03-incident.md) and [Lab 4](labs/04-fix-and-rerun.md) |
| Break | 10 minutes | none |
| 4. Build an evaluator | 01:36 to 02:11 | [Lab 5](labs/05-evals.md) |
| 5. Monitor and alert | 02:16 to 02:39 | [Lab 6](labs/06-alerts.md), optional |
| 6. Take it to production | 02:39 to 03:00 | no lab, see [docs/production-checklist.md](docs/production-checklist.md) |

Lab 0 is the setup you just did. Each lab file in [labs/](labs/) has the same steps with more detail, and [docs/](docs/) holds the extras. Every command you need is below.

If the wifi or Langfuse is down, add `--exporter console` to the commands in Labs 1 to 4. The terminal then prints the trace and sends nothing. The Langfuse clicks need a connection, so pair with a neighbour for those. Labs 5 and 6 need Langfuse.

### Lab 1. First trace

1. In your terminal, run TripMate on a request.

```
uv run ws run "Book HYD to BLR on 2026-10-31"
```

2. Read the last lines. TripMate prints its answer, then a line that starts with `trace:` and a link to the trace in Langfuse.
3. Open the link in your browser. If it does not open, go to Langfuse and click **Tracing**. Your newest trace is at the top.
4. Click the trace. You see a tree of spans on the left and the details of the selected span on the right.
5. Compare your tree with the one on the projector. Find these four things in it.
   - The top span named `tripmate`.
   - The `LangGraph` chain under it.
   - The `generation` spans. Each is one model call.
   - The `tool` spans, `search_flights` and `book_flight`.
6. Click a `tool` span. Its input shows the arguments the agent sent.

The trace page shows nested spans with timing, inputs, outputs and metadata.

You are done when your own trace shows in Langfuse with the `tripmate` span at the top. That is checkpoint 1. Put up a green sticky.

If you do not see this:

- No `trace:` link in the terminal. You probably ran with `--exporter console`. Run the command again without it.
- A `[FAIL]` or `error:` line instead. Find it in [Common errors](#common-errors).
- The trace is not in the list. Wait ten seconds, then reload the browser tab. Check that you are in the project `tripmate-workshop` and in the same region as your `LANGFUSE_BASE_URL`.

### Lab 2. Read a trace

This lab needs a lot of runs. You start them in a second terminal and keep reading while they finish.

1. In Langfuse, open the `tripmate` span from Lab 1 and look at its input and its output.
2. Open a second terminal window, as in step 1 of the setup.
3. Move into the repo in that window.

```
cd ~/AI-Agent-Observability
```

4. Send 50 runs. They take a few minutes.

```
uv run ws load -n 50
```

5. While it runs, open the [worksheet](labs/worksheet.md). With a partner if you have one, answer Part A (questions 1 to 5) from your Lab 1 trace.
6. The load prints one line per run, such as `run 1/50: PASS in 0.70s`. When it ends, its last line starts with `latency over 50 runs:` and shows the mean, p50, p95 and p99 times. Copy those four numbers into the percentile table on the worksheet.
7. Open the latency view in Langfuse for the same runs. Soumen shows where it is on the projector. Its numbers can differ a little from yours, because Langfuse times each trace on its own and may use another percentile method. See [docs/maths-appendix.md](docs/maths-appendix.md#b0-percentiles-on-small-samples).

A percentile such as p95 is the time that 95 out of 100 runs beat. With fewer than 100 runs, p99 is just the slowest run.

A short run looks like this. Your times differ.

```
run 1/5: PASS in 0.70s
...
done: 5 runs of case 0, local check PASS 5/5
latency over 5 runs: mean 0.79s, p50 0.71s, p95 0.96s, p99 0.96s (nearest rank; under 100 runs p99 is just the slowest run)
```

You are done when you can read your own p50, p95 and p99. That is checkpoint 2. The runs are seeded, so everyone's numbers are close, but laptops differ a little.

If you do not see this:

- The runs stop on an `error:` line. Find it in [Common errors](#common-errors).
- The command seems stuck. Fifty runs take a few minutes. Wait for the `done:` line.
- You are short on time. Answer questions 1 to 3 and move on.
- You are offline. Run `uv run ws load -n 50 --exporter console`. It prints the same latency line.

### Lab 3. The incident

A customer says TripMate booked the wrong flight. You find the evidence in the traces and explain what went wrong.

Use this method on the trace list in Langfuse. Each step is a separate check, so clear the previous filter before the next one.

1. Filter on level `ERROR`.
2. Filter on type `tool`.
3. Sort by duration or by tokens.
4. Compare what was asked (the input of the `tripmate` span) with what the tool did (the tool's input and output).
5. Open the `generation` span that chose the tool call.

Warm-up first. Run Case 1.

```
uv run ws case 1
```

Open the trace link it prints. One span is red. Find it and the generation that caused it. Tell your TA your answer.

Now the real complaint. Run Case 2.

```
uv run ws case 2
```

Open the trace link it prints. Nothing is red, so the level filter shows nothing. Clear it and carry on with the other steps. Fill in Part B (the evidence table) of the [worksheet](labs/worksheet.md) with your partner. Then write Part C, one sentence.

The root cause is not in this README on purpose. This repo is public, so the hints and the answer are on the slides and the TA sheet. The full lab text is in [labs/03-incident.md](labs/03-incident.md).

You are done when your sentence says what went wrong, where it shows in the trace and why the confirmation hid it. A TA checks it. That is checkpoint 3.

If you do not see this:

- You cannot find a red span in Case 2. That is expected. Case 2 has no error.
- You cannot find a filter or sort control. Its label can differ in your version of Langfuse. Look above the trace table, or ask a TA.
- You go round in circles. Go back to step 4 of the method.
- You are offline. Run the case with `--exporter console`. The output shows the requested and booking fields and every tool's arguments.

```
uv run ws case 2 --exporter console
```

### Lab 4. Fix and rerun

You now edit one file. The edit makes the agent refuse a wrong booking.

1. Open `src/tripmate/guards.py` in your editor.

macOS.

```
open -e src/tripmate/guards.py
```

Windows (PowerShell).

```
notepad src\tripmate\guards.py
```

Linux.

```
nano src/tripmate/guards.py
```

2. Find the line `# >>> WORKSHOP EDIT HERE (Lab 4) <<<`. Under it is this function.

```python
def validate_booking(requested: dict[str, str], args: dict[str, str]) -> None:
    """Raise ValueError if the booking arguments don't match what the user asked for.
    requested and args both have keys: origin, destination, date.
    TODO: compare the three fields and raise ValueError on any mismatch."""
    return
```

3. Replace the line `return` with your own code. Keep the four spaces in front of each line you write. Python needs them. Use spaces, not the Tab key.
4. Make the function raise a `ValueError` if the origin, destination or date in `args` differs from `requested`.
5. Save the file.

Here is the Python syntax you need, with unrelated names. Read a value with square brackets and quotes. Raise an error with `raise`.

```python
if left["color"] != right["color"]:
    raise ValueError("the colors differ")
```

6. Rerun Case 2. This reloads your edit.

```
uv run ws case 2 --rerun
```

7. Read the output. A `guard:` line shows what your guard did. Expect a red `book_flight` span. Your guard caught the bad call, so that red is good. Then expect a corrected booking and a last check line.

```
booking_matches_request: PASS (local check, same logic as the Langfuse evaluator)
```

8. Open the new trace in Langfuse and compare its `tripmate` span with the one from the old Case 2 trace.
9. Now turn the guard off to see the original bug again, even with your fix in place.

```
uv run ws case 2 --guard off
```

The guard stops the wrong action before it happens. The evaluator in Lab 5 checks the recorded outcome afterwards.

You are done when step 6 prints `PASS`. That is checkpoint 4. Put up a green sticky.

If you do not see this:

- The `guard:` line says `no-op`. Your guard has not rejected anything yet. Check that you removed `return` and saved the file.
- The `guard:` line says `error in guards.py` and names a Python error. Read the error. A `NameError` or `AttributeError` often means you wrote `args.origin`. Write `args["origin"]` instead. An `IndentationError` means the spaces at the start of a line are wrong.
- The check line says `FAIL`. Your code runs but does not stop the wrong booking. Check all three fields.
- You broke the file. Restore the original with `git restore src/tripmate/guards.py`, then edit again.
- Stuck for more than five minutes. Ask a TA.

More help is in [docs/troubleshooting.md](docs/troubleshooting.md#lab-4-your-guardspy-edit).

### Lab 5. Build and test an evaluator

An evaluator is a program that scores traces. Yours compares the structured request with the structured booking, not the confirmation text.

1. Optional, for Lab 6. Create the alert from [Lab 6](#lab-6-alerts-optional) steps 1 to 4 now, before any score exists. Then you can watch it go from `NO_DATA` to `ALERT`.
2. Copy the evaluator code to your clipboard. It is the whole of `evals/booking_matches.py`.

macOS.

```
pbcopy < evals/booking_matches.py
```

Windows (PowerShell).

```
Get-Content -Raw evals\booking_matches.py | Set-Clipboard
```

Linux. Open the file, select all and copy. In nano, press Ctrl and X to leave without changes.

```
nano evals/booking_matches.py
```

3. In Langfuse, open **Evaluators** in the left menu.
4. Click **New evaluator**, then choose **Code evaluator**, then choose **Python**.
5. Paste the code. Replace everything that is in the editor.
6. Set the target to the root observations named `tripmate`. Langfuse lets you filter by **Is Root Observation** and by name. Do not save yet.
7. Test first. Pick your old Case 2 trace as the sample and run the test. Expect `false`, with a comment.
8. Test again on the trace from your `--rerun`. Expect `true`.
9. Save the evaluator with a rule on new data.
10. Make fresh traffic. Run these three commands, one after the other.

```
uv run ws load -n 15 --case 0
```

```
uv run ws load -n 15 --case 2 --guard off
```

```
uv run ws case 2 --rerun
```

11. Wait a minute. In the trace list, filter on the score `booking_matches_request` equal to `false`. Only the wrong bookings stay.

The code evaluator runs in a sandbox. It can use only the Python standard library. It has no network access and a two second limit. Its traces must come from an OpenTelemetry SDK, which TripMate uses. If you are short on time, use `-n 5` instead of `-n 15`.

You are done when the evaluator says `false` on the old Case 2 trace and `true` on the rerun trace (checkpoint 5), and scores appear on the new traffic (checkpoint 6).

If you do not see this:

- The test error says `missing field`. You picked the wrong observation or an old trace. Use the `tripmate` span from a fresh run.
- You cannot find **Code evaluator**, or your TA picks the fallback. Read `src/tripmate/checks.py` and add `--score sdk` to the commands in step 10. Your terminal then scores each run and the scores arrive in Langfuse.
- No scores show after two minutes. Reload the page and check that the evaluator and its rule are saved.

### Lab 6. Alerts (optional)

An alert can tell "not measured" from "failing". You need the scores from Lab 5. Soumen demos this with two pre-built alerts on the projector, so building your own is optional. The free Hobby plan allows two alerts.

If you made the alert at the start of Lab 5, it started on `NO_DATA`. If you make it now, your Lab 5 scores already exist, so it can go straight to `ALERT`.

1. In Langfuse, open **Alerts** and click **New Alert**.
2. Choose the data source **Scores** (boolean) and the score `booking_matches_request`.
3. Choose the metric average. Choose the operator below and the threshold `0.9`. Choose the smallest window offered.
4. For no-data handling, choose **Show severity NO_DATA**, not the default. The default counts missing data as zero.
5. Save the alert.
6. Optional second alert. Count the `booking_matches_request` scores and alert below 10. Save it too. It does not silence the first alert. It tells you the pass rate rests on few scores.
7. Make failing traffic and watch the state change.

```
uv run ws load -n 40 --case 2 --guard off
```

Alert checks can take a few minutes. Reload the **Alerts** page to see the state. The workshop does not need a notification channel. If the form insists on one, ask a TA.

You are done when you can explain the difference between `NO_DATA` and `ALERT`.

If you do not see this:

- The alert stays quiet. Wait for the next window to end, or run the load command again.
- The alert says `NO_DATA`. Nothing was scored in that window. Check Lab 5.
- The form will not save. You may have reached the limit of two alerts. Delete one.
- You are short on time. Watch Soumen's alerts on the projector.

## Common errors

`ws doctor` stops at the first `[FAIL]` and prints a one-line cause and fix. `[WARN]` lines don't stop it. The `error:` and `guard:` lines come from `ws run` and `ws case`. The usual ones:

| You see | Fix |
|---|---|
| `[FAIL] no .env here; copy .env.example to .env in the repo folder` | Run the copy command from step 6 inside the repo folder |
| `error: missing LANGFUSE_PUBLIC_KEY...` | Same cause from `ws run` or `ws case`: create `.env` as in step 6, or add `--exporter console` |
| `[FAIL] paste your project's keys into .env (pk-lf-... and sk-lf-...)` | Replace the placeholders with your project's API keys |
| `[FAIL] the keys are swapped; LANGFUSE_PUBLIC_KEY starts with pk-lf-` | Swap the two key values in `.env` |
| `[FAIL] these keys belong to the US region: set LANGFUSE_BASE_URL=https://us.cloud.langfuse.com in .env` | Wrong region: set the URL the message names |
| `[FAIL] LANGFUSE_BASE_URL must stop after the host` | Keep only `https://cloud.langfuse.com` or `https://us.cloud.langfuse.com`, without `/project/...` |
| `[FAIL] Langfuse at https://cloud.langfuse.com rejected the keys (HTTP 401)` | Copy both keys again from the project settings, or create a new pair |
| `[FAIL] .env is not UTF-8 text; open it in an editor and save it as UTF-8` | Save `.env` as UTF-8 (UTF-16 from PowerShell is read automatically) |
| `[FAIL] cannot reach https://cloud.langfuse.com (ConnectError)` | Check the wifi, proxy or VPN; try a hotspot, or work offline with `--exporter console` |
| `[WARN] guards.py differs from the workshop version` | Before the workshop: `git stash push --include-untracked -m "before-workshop"` |
| `[WARN] not on the workshop version v2026.10.31` | `git fetch --tags`, then `git stash push --include-untracked -m "before-workshop"`, then `git checkout v2026.10.31`, then `uv sync` |
| `guard: error in guards.py` | Your Lab 4 edit crashed; the message names the Python error. Use `args["origin"]`, not `args.origin` |

Other things that go wrong before any message appears:

| You see | Fix |
|---|---|
| `git: command not found` or `'git' is not recognized` | Install Git (step 2), then open a new terminal |
| `uv: command not found` or `'uv' is not recognized` | Open a new terminal. If it still fails, run the install again (step 3) |
| `No such file or directory` or `Cannot find path` after a `cd` | Run `pwd`. Then run `cd ~/AI-Agent-Observability` |
| `No pyproject.toml found` or `Failed to spawn: ws` | You are in the wrong folder. Run `cd ~/AI-Agent-Observability` |
| You cannot find `.env` in your file browser | The name starts with a dot, so it is hidden. Use the `ls` command in step 6 or open it from the terminal |

Every message, with more detail, is in [docs/troubleshooting.md](docs/troubleshooting.md).

## Windows traps

- **Scripts are blocked.** PowerShell can refuse to run scripts. The uv install line already contains `-ExecutionPolicy ByPass`, which allows the installer for that one command and changes nothing else. Do not change your system policy.
- **Open a new terminal after installing uv or Git.** The old window does not see them.
- **Use PowerShell.** Command Prompt (`cmd`) does not understand `Copy-Item` or `Get-Content`.
- **Line endings.** Windows and Linux end lines differently. You do not need to change anything. The repo's own tests run on Windows.
- **Hidden files.** `ls -Force` shows `.env`. In File Explorer, turn on hidden items in the **View** menu.
- **Notepad adds `.txt`.** If you create `.env` by hand in a save dialog, the name can become `.env.txt`. Use the `Copy-Item` command in step 6 instead.

## If you are stuck

1. Read the last line the terminal printed. It usually names the cause.
2. Find that line in [Common errors](#common-errors) or in [docs/troubleshooting.md](docs/troubleshooting.md).
3. Ask the person next to you. Pairing is allowed.
4. Post the exact message in the workshop chat. Copy the text. Do not describe it.
5. On the day, put a red sticky on your laptop for a TA.

When you ask for help, say your operating system, the command you ran and the message you got. Doctor output is safe to share.

## Never share your secret key

Your secret key starts with `sk-lf-`. Anyone who has it can read and write in your Langfuse project.

- Never paste it in chat, in an email or in a GitHub issue.
- Never show your `.env` file on screen, in a screenshot or in a video.
- Never put the key in code or in a file other than `.env`. Git ignores `.env`, so it is not uploaded.
- Do not force-add `.env` with Git.
- If it leaks, open the Langfuse project **Settings** and **API Keys**, create a new key pair and delete the old one. Then update `.env`.

You may share error messages and `ws doctor` output. They do not contain your keys.

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

`--exporter console` works with every command except `doctor`. Use it if the wifi or Langfuse is down. The cases and the rerun check all work offline.

Two more flags show up in the labs. `--guard off` turns your guard off, so you can see the broken run again. `--score sdk` scores each trace from your terminal and sends the score to Langfuse. It is a fallback for when the Langfuse evaluator is not available. It needs a connection, so you cannot combine it with `--exporter console`.

## Before the workshop

You'll edit one function in `src/tripmate/guards.py` during the workshop. Any editor works. Please don't edit it before the day. If you already did, `uv run ws doctor` warns you, and the final email tells you how to set it aside.

On Friday 30 October you'll get the exact commands to switch to the final version. They look like this. Run them one at a time, in the repo folder.

```
git fetch --tags
```

```
git stash push --include-untracked -m "before-workshop"
```

```
git checkout v2026.10.31
```

```
uv sync
```

Git then prints a long note about a `detached HEAD`. That is expected. It means you are looking at a fixed version of the code.

## Privacy

The workshop uses only made-up data. Keep your keys in `.env`, which git ignores. Never share your secret key in chat or on screen. If it leaks, rotate it in the Langfuse project settings.

## Sponsor

If this project helps you, consider [sponsoring my work on GitHub](https://github.com/sponsors/soumendrak). Your support helps fund maintenance, documentation and continued development.
