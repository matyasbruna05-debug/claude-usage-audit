---
name: claude-audit
description: Audit how a person works with Claude Code (CLI or desktop app). Computes numbers from their local transcripts, scores eight areas against a fixed rubric, places them on an S–F scale and gives three concrete steps to improve. Works on your own usage or, with their consent, on someone else's (a teammate, a client), from their machine or from data they send. Use when someone says "audit my Claude usage", "how good am I at working with Claude", "review how I prompt", "where am I on the scale", "audit my team's Claude usage", "repeat the audit", or asks the same in any other language. Not for checking one finished task and not for code review.
---

# Claude usage audit

The output is a short report: a level, a score per area, findings with evidence, and the three steps with the largest effect. The method follows how experienced designers and researchers run audits:

- **Evidence before opinion.** Every claim carries a number or a verbatim example. Interpretation is labelled as interpretation.
- **Context before judgement.** The same number means different things for a programmer and for someone who writes copy. Score against the person's goal.
- **One rubric for everyone.** Points come from `references/rubric.md`, so audits compare across people and over time.
- **Few findings, ranked.** Seven at most, by severity and effort. Nobody acts on twenty.
- **Behaviour, not the person.** No flattery, no put-downs. Always include what works.
- **Say what the audit did not see.** Sample size, missing sources, estimates.
- **A second pair of eyes.** An author is lenient towards their own conclusions, so an independent reviewer reads them.

Write the report in the language the person uses with you. The files in this skill stay in English.

## Roles and models

Two roles: an **auditor**, who reads the data and writes the report, and a **reviewer**, who reads only the draft and challenges it. The reviewer must not share the auditor's context.

- With subagents: run the auditor as a subagent on a strong, cost-efficient model and the reviewer as a separate subagent on the strongest model available. The reviewer reads little, so this stays cheap. Whichever role matches the model the session already runs on can be done in the session itself.
- With a single model: run the reviewer as a fresh subagent on that model.
- Without subagents: do the review yourself as a separate pass against the checklist in step 5, and say in the report that no independent review took place.

State in the report which models filled which role.

## Workflow

### 1. Whose data, and with consent
Transcripts hold everything a person typed to Claude. Audit someone else only with their knowledge. Three routes, most private first:

- **They run the audit themselves** on their own machine. Nothing leaves it.
- **They send only `audit-data.json`**: they run the collector (with `--samples 0` if they do not want to share example prompts) and send the file. The audit then runs without transcripts, with lower confidence in findings that need examples.
- **They send a copy of their transcript folder**, only if they choose to. Delete the copy after the audit and say so.

Keep another person's outputs out of version control and send them nowhere without instruction.

### 2. Collect
Run the collector that ships next to this file (`<skill>` is the folder containing this SKILL.md):

```bash
python3 <skill>/scripts/collect.py --out <folder>/audit-data.json
```

On Windows use `python` or `py -3`. Someone else's data: `--dir <copy of projects> --home <copy of their Claude folder>`. Period: `--days 60` (default), `--days 0` for everything. The script only reads. It prints a summary and saves numbers plus example prompts in which secrets, e-mail addresses, phone numbers and the home path are masked. Exit code 2 means there is nothing to audit; say so and do not guess.

The collector sees Claude Code and the desktop app's code sessions on that machine. It does not see chats on claude.ai, mobile, or other tools.

### 3. Context
Find out (ask, unless it is clear from the conversation or their CLAUDE.md): what the person does and what they use Claude for, whether they write code, and how much of their work with Claude happens elsewhere. If you cannot ask, continue and record your assumptions under "What the audit did not see".

### 4. Audit (auditor)
1. Read `audit-data.json`, `references/rubric.md` and `references/report-template.md`.
2. For each area write the observation from the data first, then the points.
3. Verify doubtful hypotheses in the transcripts with at most five targeted looks (search by the `session` id from a sample; never read whole files). Above all: did a vague prompt really cost extra rounds? Are the "possible correction rounds" corrections of Claude's mistakes, or new requests?
4. Look at one or two CLAUDE.md files and the list of skills for area 6.
5. Write the draft report to a file, following the template.

Take numbers from the file; do not recompute them in your head. The collector's word lists are coarse (especially correction rounds, visual prompts and vague words), so never turn one into a finding without an example that confirms it.

### 5. Review (reviewer), one round
The reviewer gets only the draft, `audit-data.json` and the rubric, with this brief:

> This is a draft audit of someone's work with Claude, written by another model. Find: claims the data does not support, points that do not match the rubric, alternative explanations the author did not consider, recommendations in the wrong order, and recommendations that are not a change of behaviour. Say whether the level is right. Return at most ten short remarks, each with what to change. Do not rewrite the report.

The auditor applies each remark or notes why not. No second round unless the level changes.

### 6. Check and hand over
- Every number in the report matches `audit-data.json`.
- The report holds no secret, e-mail address, phone number or third person's name.
- The first section stands on its own.

Then in chat: the level, the three steps, and where the report is. When one person ran the audit for another, the report belongs to the audited person; give it to whoever asked only with their consent.

## Repeat audits and teams
- **Again later:** run the collector with the same `--days`, compare with the previous `audit-data.json`, add a "last time" column, and measure progress on the numbers from "Next measurement".
- **Team:** each person gets their own data file and report. A shared summary may hold only the table of points per area and common patterns (what most people lack), never individuals' example prompts. Do not rank people unless they explicitly ask.
