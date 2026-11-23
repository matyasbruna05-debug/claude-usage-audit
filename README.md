# claude-audit

A skill for Claude Code that audits **how you work with Claude** and tells you what to change.

It reads your local Claude Code transcripts, computes numbers (how you brief, how often you ask for proof, which models you use, where your work ends up), scores eight areas against a fixed rubric, places you on an **S–F scale** and gives you the three steps with the largest effect. Every claim in the report carries a number or one of your own prompts as evidence.

It works on your own usage, or, with their consent, on a teammate's.

> **Status: early version.** The collector is covered by tests on synthetic transcripts in both the CLI and desktop-app formats, but the full audit has so far been validated on one person, on the macOS desktop app. The rubric thresholds are provisional. Treat the level as a starting point for a conversation, not a verdict. Reports of what did not fit are welcome in the issues.

## What you get

An excerpt in the shape of a real report. The person and the numbers are invented:

```markdown
# Claude usage audit: Alex
31 sessions, 412 prompts · confidence: good
Auditor: <model> · Reviewer: <model>

## Result
**Level B** (19/32). You have a system (rules, skills, automation), but single prompts do not use it.
Three steps with the largest effect:
1. Attach a reference to every visual task and say what must not change → fewer "put it back" rounds
2. End bigger tasks with "done when…" and ask for proof → fewer fixes after hand-over
3. New topic = new session in the project folder → shorter context, lower spend

## Findings
### 1. Visual prompts without a reference cost extra rounds · severity 3
- **Observation:** 40 visual prompts, a reference on 22% of them.
- **Evidence:** "make it look more modern" → two prompts later: "why is this better than before?" → "revert the corners"
- **Recommendation:** before → better: "The booking page feels crowded on mobile. Model it on [screenshot]:
  large spacing, one strong heading. Keep the colours from the approved demo."
```

## Install

Needs Claude Code and Python 3.8 or newer. No other dependencies.

macOS / Linux:

```bash
git clone https://github.com/matyasbruna05-debug/claude-audit ~/.claude/skills/claude-audit
```

Windows (PowerShell):

```powershell
git clone https://github.com/matyasbruna05-debug/claude-audit "$env:USERPROFILE\.claude\skills\claude-audit"
```

Then start a new Claude Code session and say:

```text
audit my Claude usage
```

Any language works; the report comes back in the language you use. To update later, run `git pull` in the skill folder.

## How it works

1. **Collect.** `scripts/collect.py` reads your transcripts and writes `audit-data.json`: numbers plus example prompts with secrets, e-mail addresses, phone numbers and your home path masked. It takes a couple of seconds.
2. **Audit.** An auditor model scores eight areas (0–4 points each) using `references/rubric.md` and checks doubtful numbers against the transcripts with a few targeted looks.
3. **Review.** A second, independent model reads only the short draft and challenges it: unsupported claims, wrong scores, wrong priorities.
4. **Report.** Level, score per area, at most seven findings with evidence, what the audit could not see, and what to measure next time.

The eight areas: briefing · context and references · verifying results · model and mode for the task · use of tools · system and learning from mistakes · project hygiene · safety and cost.

## Privacy

- The collector is **read-only** and makes **no network requests**. It is one standard-library Python file; read it before you run it.
- Your transcripts are read on your machine. What the auditor model sees is `audit-data.json` and a few targeted looks into transcripts, inside your own Claude Code session, under the same terms as the rest of your work there.
- To audit someone else, the most private route is that they run it themselves. They can also send only `audit-data.json`, with `--samples 0` if they do not want to share any prompt text. Never audit someone without their knowledge.

## What it does not see

- Chats on claude.ai, the mobile app, or other AI tools.
- Whether a result was actually good. It measures behaviour (how you brief, check and organise), not outcomes.
- Nuance in wording. The collector finds candidates with coarse word lists; the auditor has to confirm each one on a real example before it becomes a finding.

## Run the collector on its own

```bash
python3 scripts/collect.py --out audit-data.json            # last 60 days
python3 scripts/collect.py --days 0 --samples 0             # everything, numbers only
python3 scripts/collect.py --dir <projects copy> --home <claude folder copy>
```

`CLAUDE_CONFIG_DIR` is respected. Exit code 2 means there was nothing to audit.

## Languages

Signal words live in `scripts/wordlists.json`, currently English and Czech. To add yours, copy the `en` block, translate it and open a pull request. Without a list for your language the audit still runs, but the numbers for vague words, correction rounds and approvals will be too low, and the auditor should be told.

## Tests

```bash
python3 -m unittest discover tests
```

The fixtures are synthetic. No real transcripts are in this repository.

## Contributing

Most useful right now: word lists for more languages, reports of transcript formats the collector misreads (with a minimal invented example, never real transcripts), and feedback on rubric thresholds from your own audits.

## Author

Made by Matyáš Brůna ([@matyasbruna05-debug](https://github.com/matyasbruna05-debug)), built together with Claude. MIT licence.

Not affiliated with or endorsed by Anthropic. "Claude" is a trademark of Anthropic.
