# Audit rubric

Eight areas, 0–4 points each. Points follow observed behaviour, not impressions. Each area lists the fields of `audit-data.json` to start from. The thresholds are provisional guides, not norms: when the person's context (role, goal, type of work) explains a number, follow the context and say so in the report.

Points in general: **0** absent · **1** rare, accidental · **2** sometimes, no system · **3** mostly, deliberate · **4** consistent and visible in the results.

## 1. Briefing
Does Claude get it right the first time?
- Data: `prompting.median_chars`, `under_40_chars_pct`, `big_tasks_briefed_under_60_chars_pct`, `with_vague_word_pct`, `vague_words`; samples "vague word" and "short prompt, big task".
- A short prompt is not a fault in itself. The fault is a short or vague prompt for a big task whose result depends on something only the person knows. Plain approvals ("yes, continue") are already excluded from these numbers; check the samples for others the collector missed.
- 4: for big tasks states the goal, the audience, what must not change and when to stop; vague words are rare. 2: mixed; around a third of big tasks briefed in under 60 characters. 0: one-word prompts even for big tasks, vague words routine.

## 2. Context and references
Does Claude get to see what it needs?
- Data: `with_attachment_or_link_pct`, `with_image`, `visual_with_reference_pct`; samples "possible good practice".
- 4: visual and content work always comes with a reference, file or example. 2: a reference on a quarter to a half of visual prompts. 0: never attaches anything.

## 3. Verifying results
Do they know it is done before it goes out?
- Data: `verification.*`, mainly `possible_correction_rounds_pct`, `prompts_with_criteria_or_proof_request_pct`, `sessions_with_3plus_corrections`; skills, hooks or rules for checking in `setup`; tests in the projects.
- 4: "done" criteria stated up front, proof with every result, correction rounds under 5%. 2: asks for a check now and then, correction rounds 10–15%. 0: finds errors only after hand-over, correction rounds above 20%.

## 4. Model and mode for the task
- Data: `models` (share of responses and tokens), `tools.sessions_with_plan`, `sessions_with_subagent`, `slash_commands` (/model).
- 4: the expensive model for hard problems, a cheap one for routine and automation, a plan for large unclear tasks. 2: nearly everything on one model, switches occasionally. 0: unaware a choice exists.
- One model for everything is not automatically a fault (subscription, simplicity). Judge by whether it costs the person limits or time.

## 5. Use of tools
- Data: `tools.skills_invoked`, `most_used`, `automated_messages` (scheduled tasks), `setup.skills`, `agents`, `commands`.
- 4: uses skills, connectors and automation regularly and to the point. 2: has them installed, uses them rarely. 0: chat only.
- The number of installed things earns nothing. Usage counts.

## 6. System and learning from mistakes
- Data: `setup.global_claude_md_lines`, `memory_files`, `projects.list[].claude_md`; while verifying, look into one or two CLAUDE.md files.
- 4: rules live in CLAUDE.md and skills; a repeated mistake gets written down and stops happening. 2: CLAUDE.md only in places, or not followed. 0: every session starts from zero.

## 7. Project hygiene
- Data: `projects.sessions_left_in_temp_pct` (and `sessions_started_in_temp_pct`), `list[].git`, `commits`, `claude_md`.
- 4: every piece of work has a folder, a history and a description. 2: half and half. 0: everything in temporary folders with no history.
- Do not demand git from people who do not write code (copy, analysis). A permanent folder and a description are enough.

## 8. Safety and cost
- Data: `safety.prompts_with_secret`, `tools.permission_modes`, `models` (tokens), session length.
- 4: no secrets in chat, knows what things cost, keeps context short. 2: an isolated leak, or no view of spend. 0: passwords and keys in chat routinely.
- Any secret in a prompt caps this area at 2 points and makes a finding of severity 3 or higher. Confirm on the masked sample that it is a real secret first; the pattern can misfire on long identifiers.

## Level

| Total | Level | What it looks like |
|---|---|---|
| 29–32 | **S** | Work runs without them and checks itself |
| 24–28 | **A** | Briefs land first time, results come with proof, model fits the task |
| 18–23 | **B** | Has a system and automation, with gaps in briefing or checking |
| 12–17 | **C** | Hands Claude tasks, no system |
| 6–11 | **D** | Mostly chats, the odd task |
| 0–5 | **F** | Questions and answers only |

Caps: Verifying results (3) at 0–1 points means **B** at most. Any area at 0 points means **A** at most. With "low" confidence give the level as an estimate with a range (for example "C to B").

## Severity of a finding (0–4)
0 not a problem · 1 cosmetic · 2 slows things down · 3 regularly costs time, money or quality · 4 a risk (leaked credentials, a mistake in front of people, lost data).

Order of recommendations = severity × how often it happens, divided by the effort to change. Quick wins (large effect, small effort) go first.
