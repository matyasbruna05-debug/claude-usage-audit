# Report template

Save as `claude-audit-<name>-<YYYY-MM-DD>.md`. Write in the person's language, plainly, without jargon (explain a term such as "subagent" in one sentence the first time). The whole report fits two to three screens; someone who reads only the first section must know the level and what to do.

```markdown
# Claude usage audit: <name>
<date> · <N> sessions, <N> prompts, <from>–<to> · confidence: <low/medium/good>
Auditor: <model> · Reviewer: <model, or "none">

## Result
**Level <X>** (<total>/32). <One sentence why.>
Three steps with the largest effect:
1. <what to do> → <what it brings>
2. …
3. …

## Score by area
| Area | Points | Main evidence |
|---|---|---|
| Briefing | <n>/4 | <number from the data, one line> |
| … | | |

## What works (keep it)
- <strength> – <evidence>

## Findings
### 1. <finding> · severity <0–4>
- **Observation:** <what the data shows, with a number>
- **Evidence:** <the number and one or two verbatim example prompts>
- **Impact:** <what it costs: extra rounds, time, tokens, risk>
- **Recommendation:** <a concrete change of behaviour; for prompts show "before → better">
- **Effort:** small / medium / large

(seven findings at most, in order of recommendation)

## What the audit did not see
- <chats outside Claude Code, work on another device, missing context>
- <where a conclusion is an estimate, and why>

## Next measurement
Again in <2–4> weeks. Track: <3–5 numbers with today's value and a target>.
```

Rules for the content:
- Every claim has a number or an example. Mark interpretation as interpretation ("it looks as if…").
- Take examples from `samples` in the data; they are already masked. Put no secrets, e-mail addresses, phone numbers or third persons' names in the report.
- Judge behaviour, not the person. No flattery, no put-downs.
- A recommendation is a change of behaviour, not a purchase or an installation. Suggest a new skill or rule only where the data shows the same mistake repeating.
- On a repeat audit add a "last time" column to the table and a "What changed" section.
