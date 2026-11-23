#!/usr/bin/env python3
"""Collect usage metrics for a Claude Code audit. Read-only: changes nothing, sends nothing.

Usage:
  python3 collect.py [--dir TRANSCRIPTS] [--home CLAUDE_DIR] [--days 60] [--out audit-data.json]
                     [--samples 60] [--lang en,cs]

--dir      folder with transcripts (default: <claude dir>/projects)
--home     the person's Claude config folder (default: $CLAUDE_CONFIG_DIR, else ~/.claude,
           else the parent of --dir); used for settings and the list of installed skills
--days     how many recent days to include (0 = everything)
--samples  how many example prompts to store (0 = none; numbers only)
--lang     which word lists from wordlists.json to use (default: all)

Output: a JSON file with numbers and example prompts. Secrets, e-mail addresses, phone
numbers and the home-directory path are masked in the examples.
Exit code: 0 = data collected, 2 = nothing to audit or bad input.
Needs Python 3.8+, standard library only.
"""
import argparse, collections, glob, json, os, re, statistics, subprocess, sys
from datetime import datetime, timedelta, timezone

for stream in (sys.stdout, sys.stderr):  # Windows consoles are often not UTF-8
    try:
        stream.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
USER_HOME = os.path.expanduser('~')

ap = argparse.ArgumentParser(description='Collect Claude Code usage metrics for an audit (read-only).')
ap.add_argument('--dir')
ap.add_argument('--home')
ap.add_argument('--days', type=int, default=60)
ap.add_argument('--out', default='audit-data.json')
ap.add_argument('--samples', type=int, default=60)
ap.add_argument('--lang', default='')
a = ap.parse_args()

if a.home:
    home = os.path.abspath(os.path.expanduser(a.home))
elif a.dir:
    home = os.path.dirname(os.path.abspath(os.path.expanduser(a.dir)))
else:
    home = os.path.abspath(os.path.expanduser(os.environ.get('CLAUDE_CONFIG_DIR') or '~/.claude'))
root = os.path.abspath(os.path.expanduser(a.dir)) if a.dir else os.path.join(home, 'projects')
if not os.path.isdir(root):
    print(f'Transcript folder not found: {root}', file=sys.stderr)
    sys.exit(2)
files = sorted(glob.glob(os.path.join(root, '*', '*.jsonl')) + glob.glob(os.path.join(root, '*.jsonl')))
since = datetime.now(timezone.utc) - timedelta(days=a.days) if a.days else None

# ---- signal words -------------------------------------------------------------------------
try:
    with open(os.path.join(HERE, 'wordlists.json'), encoding='utf-8') as fh:
        WL = {k: v for k, v in json.load(fh).items() if not k.startswith('_')}
except (OSError, ValueError) as e:
    print(f'Cannot read wordlists.json next to this script: {e}', file=sys.stderr)
    sys.exit(2)
langs = [x.strip() for x in a.lang.split(',') if x.strip()] or sorted(WL)
unknown = [x for x in langs if x not in WL]
if unknown:
    print(f'Unknown language(s) {unknown}; available: {sorted(WL)}', file=sys.stderr)
    sys.exit(2)

def merged(key):
    seen, out = set(), []
    for lang in langs:
        for item in WL[lang].get(key, []):
            if item.lower() not in seen:
                seen.add(item.lower())
                out.append(item)
    return out

def alt(key):
    items = merged(key)
    return '(?:' + '|'.join(items) + ')' if items else r'(?!x)x'

VAGUE = merged('vague')
FIX = re.compile(alt('fix'), re.I)
DONE = re.compile(alt('done_criteria'), re.I)
VISUAL = re.compile(alt('visual'), re.I)
PING = re.compile(r'^\W*' + alt('status_ping') + r'\b.{0,25}\??\s*$', re.I)
APPROVAL = re.compile(r'^\W*(?:' + '|'.join(re.escape(x) for x in merged('approval')) + r')(?:\W+(?:' +
                      '|'.join(re.escape(x) for x in merged('approval')) + r'))*\W*$', re.I)

SECRET = re.compile(
    r'(sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_\w{20,}|xox[abprs]-[A-Za-z0-9-]{10,}'
    r'|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}|eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}'
    r'|-----BEGIN [A-Z ]*PRIVATE KEY-----|\b[A-Za-z]{2,10}_(?:live_|test_|secret_|key_)?(?=[A-Za-z0-9]*\d)(?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9]{24,}\b'
    r'|Bearer\s+[A-Za-z0-9._-]{20,}'
    r'|(?:password|passwd|pwd|heslo|api[_ -]?key|token|secret)\s*(?:is|je|[:=])\s*\S{6,})', re.I)
MAIL = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
PHONE = re.compile(r'(?<![\w.])\+?\d[\d ()-]{8,}\d(?![\w.])')
REF = re.compile(r'(https?://\S+|(?:~|\.|/|[A-Za-z]:\\)?[\w./\\-]+\.(?:png|jpe?g|gif|webp|pdf|fig|html|md|csv|xlsx?|docx?|pptx?|mp4|mov|svg|json|tsx?|jsx?|py)\b'
                 r'|\[Image|@[\w./-]+\.\w+)', re.I)
TEMP = re.compile(r'(scratch|[/\\]te?mp[/\\]|[/\\]private[/\\]tmp|[/\\]var[/\\]folders|AppData[/\\]Local[/\\]Temp|[/\\]Downloads\b|[/\\]Desktop\b)', re.I)

def clean(t):
    return re.sub(r'<system-reminder>.*?</system-reminder>', '', t, flags=re.S).strip()

def tilde(p):
    return ('~' + p[len(USER_HOME):]) if p and USER_HOME not in ('', '/') and p.startswith(USER_HOME) else p

def redact(t):
    t = SECRET.sub('[SECRET]', t)
    t = MAIL.sub('[EMAIL]', t)
    t = PHONE.sub('[PHONE]', t)
    if USER_HOME not in ('', '/'):
        t = t.replace(USER_HOME, '~')
    return t

def word_hit(text, w):
    return re.search(r'(?<!\w)' + re.escape(w) + r'(?!\w)', text, re.I) is not None

def is_temp(p):
    p = p or ''
    return bool(TEMP.search(p)) or p.rstrip('/\\') == USER_HOME.rstrip('/\\')

# ---- read transcripts ---------------------------------------------------------------------
prompts, sessions = [], []
models, tokens_out, tokens_in = collections.Counter(), collections.Counter(), collections.Counter()
tools, skills, auto, perm_modes, slash = (collections.Counter() for _ in range(5))
seen_msg = set()
secret_prompts = interrupts = bad_lines = 0
first_ts = last_ts = None

for f in files:
    s = {'id': os.path.basename(f)[:8], 'cwd': None, 'moved_to': None, 'prompts': 0, 'tools': 0, 'agents': 0,
         'plan': False, 'from': None, 'to': None, 'fixes': 0}
    sp = []
    try:
        fh = open(f, encoding='utf-8', errors='ignore')
    except OSError:
        continue
    with fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                bad_lines += 1
                continue
            if not isinstance(d, dict):
                continue
            typ = d.get('type')
            if typ == 'relocated' and d.get('relocatedCwd'):
                s['moved_to'] = d['relocatedCwd']
                continue
            ts = d.get('timestamp')
            if ts and since:
                try:
                    if datetime.fromisoformat(str(ts).replace('Z', '+00:00')) < since:
                        continue
                except ValueError:
                    pass
            if d.get('isSidechain'):
                continue
            if ts and typ in ('user', 'assistant'):
                s['from'] = s['from'] or ts
                s['to'] = ts
            if typ == 'assistant':
                m = d.get('message') or {}
                mid = m.get('id') or d.get('uuid')
                if mid not in seen_msg:
                    seen_msg.add(mid)
                    model = m.get('model') or '?'
                    if model != '<synthetic>':
                        models[model] += 1
                        u = m.get('usage') or {}
                        tokens_out[model] += u.get('output_tokens') or 0
                        tokens_in[model] += ((u.get('input_tokens') or 0) + (u.get('cache_creation_input_tokens') or 0)
                                             + (u.get('cache_read_input_tokens') or 0))
                content = m.get('content')
                for c in content if isinstance(content, list) else []:
                    if isinstance(c, dict) and c.get('type') == 'tool_use':
                        n = c.get('name') or '?'
                        inp = c.get('input') or {}
                        srv = n.split('__')[1] if n.startswith('mcp__') and n.count('__') >= 2 else None
                        tools[n if srv is None else 'connector (MCP)' if re.fullmatch(r'[0-9a-f-]{30,}', srv) else 'MCP ' + srv] += 1
                        s['tools'] += 1
                        if n == 'Skill':
                            skills[str(inp.get('skill') or inp.get('command'))] += 1
                        if n in ('Agent', 'Task', 'Workflow'):
                            s['agents'] += 1
                        if n in ('ExitPlanMode', 'EnterPlanMode'):
                            s['plan'] = True
            if typ != 'user' or d.get('isMeta'):
                continue
            kind = (d.get('origin') or {}).get('kind') or ''
            if (d.get('promptSource') == 'system' or kind.startswith('task-notification')
                    or d.get('turnOrigin') in ('host_synthetic', 'scheduled', 'task_notification')):
                auto[d.get('turnOrigin') or kind or 'system'] += 1  # automated message, not a human prompt
                continue
            s['cwd'] = s['cwd'] or d.get('cwd')
            if d.get('permissionMode'):
                perm_modes[d['permissionMode']] += 1
                if d['permissionMode'] == 'plan':
                    s['plan'] = True
            c = (d.get('message') or {}).get('content')
            img = False
            if isinstance(c, list):
                if any(isinstance(x, dict) and x.get('type') == 'tool_result' for x in c):
                    continue
                img = any(isinstance(x, dict) and x.get('type') == 'image' for x in c)
                t = ' '.join(x.get('text', '') for x in c if isinstance(x, dict) and x.get('type') == 'text')
            else:
                t = c if isinstance(c, str) else ''
            t = clean(t)
            if not t:
                if img and sp:
                    sp[-1]['img'] = sp[-1]['ref'] = True  # image sent on its own right after a prompt
                continue
            if 'Request interrupted' in t:
                interrupts += 1
                continue
            cm = re.search(r'<command-name>\s*(/?[\w:.-]+)', t)
            if cm:
                slash[cm.group(1)] += 1
                continue
            if t.startswith('<') or t.startswith('This session is being continued') or t.startswith('Caveat'):
                continue
            p = {'text': t, 'len': len(t), 'img': img, 'ref': bool(REF.search(t)) or img, 'secret': bool(SECRET.search(t)),
                 'vague': [w for w in VAGUE if word_hit(t, w)], 'fix': bool(FIX.search(t)), 'ping': bool(PING.match(t)),
                 'done': bool(DONE.search(t)), 'visual': bool(VISUAL.search(t)),
                 'approval': len(t) <= 60 and bool(APPROVAL.match(t)), 'tools_after': 0, 'session': s['id'], '_base': s['tools']}
            secret_prompts += p['secret']
            s['fixes'] += p['fix']
            s['prompts'] += 1
            if sp:
                sp[-1]['tools_after'] = s['tools'] - sp[-1]['_base']
            sp.append(p)
    if sp:
        sp[-1]['tools_after'] = s['tools'] - sp[-1]['_base']
        prompts += sp
        sessions.append(s)
        if s['from']:
            first_ts = min(x for x in (first_ts, s['from']) if x)
            last_ts = max(x for x in (last_ts, s['to']) if x)

if not prompts:
    print(f'No human prompts found in {root} for the chosen period ({len(files)} transcript files). '
          f'Try --days 0 or another folder.', file=sys.stderr)
    sys.exit(2)

# ---- projects -----------------------------------------------------------------------------
proj = collections.OrderedDict()
for s in sessions:
    s['home'] = s['moved_to'] or s['cwd'] or '?'  # where the work ended up
    r = proj.setdefault(s['home'], {'folder': tilde(s['home']), 'sessions': 0, 'prompts': 0,
                                    'temporary': is_temp(s['home']), 'exists': os.path.isdir(s['home'])})
    r['sessions'] += 1
    r['prompts'] += s['prompts']
for path, r in proj.items():
    if not r['exists']:
        continue
    r['claude_md'] = os.path.isfile(os.path.join(path, 'CLAUDE.md'))
    try:
        top = subprocess.run(['git', '-C', path, 'rev-parse', '--show-toplevel'], capture_output=True, text=True, timeout=5)
        r['git'] = top.returncode == 0
        if r['git']:
            n = subprocess.run(['git', '-C', path, 'rev-list', '--count', 'HEAD'], capture_output=True, text=True, timeout=5)
            r['commits'] = int(n.stdout.strip() or 0) if n.returncode == 0 else 0
            r['claude_md'] = r['claude_md'] or os.path.isfile(os.path.join(top.stdout.strip(), 'CLAUDE.md'))
    except (OSError, subprocess.SubprocessError, ValueError):
        r['git'] = None

def ls(sub):
    d = os.path.join(home, sub)
    return sorted(x for x in os.listdir(d) if not x.startswith('.')) if os.path.isdir(d) else []

setup = {'folder': tilde(home), 'global_claude_md_lines': None, 'skills': ls('skills'), 'agents': ls('agents'),
         'commands': ls('commands'), 'hooks': [], 'allowed_commands': 0,
         'memory_files': len([x for x in glob.glob(os.path.join(root, '*', 'memory', '*.md')) if not x.endswith('MEMORY.md')])}
g = os.path.join(home, 'CLAUDE.md')
if os.path.isfile(g):
    with open(g, encoding='utf-8', errors='ignore') as fh:
        setup['global_claude_md_lines'] = sum(1 for _ in fh)
try:
    with open(os.path.join(home, 'settings.json'), encoding='utf-8') as fh:
        st = json.load(fh)
    setup['hooks'] = sorted((st.get('hooks') or {}).keys())
    setup['allowed_commands'] = len(((st.get('permissions') or {}).get('allow')) or [])
except (OSError, ValueError, AttributeError):
    pass

# ---- numbers ------------------------------------------------------------------------------
def pct(x, of):
    return round(100 * x / of, 1) if of else 0

n = len(prompts)
real = [p for p in prompts if not p['approval']]  # prompts that actually brief something
L = [p['len'] for p in real] or [0]
vis = [p for p in real if p['visual']]
big = [p for p in real if p['tools_after'] >= 15]
vague_c = collections.Counter(w for p in real for w in p['vague'])
tot_resp = sum(models.values())
ns = len(sessions)

def sample(ps, k, why):
    return [{'why': why, 'session': p['session'], 'tool_calls_after': p['tools_after'],
             'text': redact(p['text'][:320]).replace('\n', ' / ')} for p in ps[:k]]

samples = []
if a.samples > 0:
    k = max(3, a.samples // 6)
    samples = (sample(sorted([p for p in real if p['vague']], key=lambda p: -p['tools_after']), k, 'vague word')
               + sample(sorted([p for p in big if p['len'] < 60], key=lambda p: -p['tools_after']), k, 'short prompt, big task')
               + sample([p for p in real if p['fix']], k, 'possible correction round')
               + sample([p for p in real if p['ping']], max(2, k // 2), 'status ping')
               + sample(sorted(real, key=lambda p: -p['len']), max(2, k // 2), 'longest prompt')
               + sample(sorted([p for p in real if p['done'] or (p['ref'] and p['len'] > 150)], key=lambda p: -p['len']), k,
                        'possible good practice (criteria, proof, reference)'))

out = {
    'schema': 1, 'created': datetime.now().isoformat(timespec='minutes'), 'source': tilde(root),
    'period_days': a.days or 'all', 'languages': langs,
    'scope': {'sessions': ns, 'prompts': n, 'from': first_ts, 'to': last_ts, 'unreadable_lines': bad_lines,
              'confidence': 'low (under 50 prompts)' if n < 50 else 'medium (50-200 prompts)' if n < 200 else 'good (200+ prompts)'},
    'prompting': {'approvals_excluded': n - len(real), 'median_chars': statistics.median(L), 'mean_chars': round(statistics.mean(L)),
                  'under_40_chars_pct': pct(sum(x < 40 for x in L), len(real)), 'over_500_chars_pct': pct(sum(x > 500 for x in L), len(real)),
                  'with_attachment_or_link_pct': pct(sum(p['ref'] for p in real), len(real)),
                  'with_image': sum(p['img'] for p in real),
                  'vague_words': dict(vague_c.most_common(12)), 'with_vague_word_pct': pct(sum(bool(p['vague']) for p in real), len(real)),
                  'visual_prompts': len(vis), 'visual_with_reference_pct': pct(sum(p['ref'] for p in vis), len(vis)),
                  'big_tasks': len(big), 'big_tasks_briefed_under_60_chars_pct': pct(sum(p['len'] < 60 for p in big), len(big))},
    'verification': {'possible_correction_rounds_pct': pct(sum(p['fix'] for p in real), len(real)),
                     'prompts_with_criteria_or_proof_request_pct': pct(sum(p['done'] for p in real), len(real)),
                     'status_pings_pct': pct(sum(p['ping'] for p in real), len(real)), 'interruptions': interrupts,
                     'sessions_with_3plus_corrections': sum(s['fixes'] >= 3 for s in sessions)},
    'models': {m: {'responses': c, 'share_pct': pct(c, tot_resp), 'output_tokens': tokens_out[m], 'input_tokens_incl_cache': tokens_in[m]}
               for m, c in models.most_common()},
    'tools': {'most_used': dict(tools.most_common(15)), 'skills_invoked': dict(skills.most_common()),
              'slash_commands': dict(slash.most_common(10)), 'sessions_with_plan': sum(s['plan'] for s in sessions),
              'sessions_with_subagent': sum(s['agents'] > 0 for s in sessions), 'permission_modes': dict(perm_modes),
              'automated_messages': dict(auto)},
    'projects': {'folders': len(proj),
                 'sessions_started_in_temp_pct': pct(sum(is_temp(s['cwd']) for s in sessions), ns),
                 'sessions_left_in_temp_pct': pct(sum(is_temp(s['home']) for s in sessions), ns),
                 'list': sorted(proj.values(), key=lambda r: -r['prompts'])[:25]},
    'safety': {'prompts_with_secret': secret_prompts},
    'setup': setup,
    'samples': samples,
}
with open(a.out, 'w', encoding='utf-8') as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)

z, o = out['prompting'], out['verification']
print(f"Audit data: {ns} sessions, {n} prompts, {str(first_ts)[:10]} to {str(last_ts)[:10]}. Confidence: {out['scope']['confidence']}.")
print(f"Prompting: median {z['median_chars']} chars, {z['under_40_chars_pct']}% under 40 chars, "
      f"{z['with_attachment_or_link_pct']}% with attachment/link, vague word in {z['with_vague_word_pct']}% "
      f"({z['approvals_excluded']} plain approvals excluded).")
print(f"Verification: possible correction rounds {o['possible_correction_rounds_pct']}%, criteria/proof asked in "
      f"{o['prompts_with_criteria_or_proof_request_pct']}%, status pings {o['status_pings_pct']}%.")
print('Models: ' + ', '.join(f"{k} {v['share_pct']}%" for k, v in list(out['models'].items())[:5]))
print(f"Tools: skills {sum(skills.values())}x, plan mode in {out['tools']['sessions_with_plan']} sessions, "
      f"subagents in {out['tools']['sessions_with_subagent']}.")
print(f"Projects: {len(proj)} folders, {out['projects']['sessions_left_in_temp_pct']}% of sessions left in a temporary folder. "
      f"Secrets pasted into prompts: {secret_prompts}.")
print(f"Saved: {os.path.abspath(a.out)} ({len(samples)} samples)")
