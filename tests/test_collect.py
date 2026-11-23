"""Tests for scripts/collect.py on synthetic transcripts. Run: python3 -m unittest discover tests

The fixtures are invented. They cover both transcript shapes the collector must read:
the desktop app (records carry promptSource / origin / turnOrigin) and the plain CLI (they do not).
"""
import json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLLECT = os.path.join(ROOT, 'scripts', 'collect.py')
NOW = '2099-01-0{}T10:00:00.000Z'  # far future so --days never filters the fixtures out


def user(text, n=1, **extra):
    return dict({'type': 'user', 'timestamp': NOW.format(n), 'cwd': '/work/shop', 'message': {'role': 'user', 'content': text}}, **extra)


def assistant(mid, model, tool_names=(), n=1):
    content = [{'type': 'text', 'text': 'ok'}] + [{'type': 'tool_use', 'name': t, 'input': {'skill': 'checker'} if t == 'Skill' else {}} for t in tool_names]
    return {'type': 'assistant', 'timestamp': NOW.format(n),
            'message': {'id': mid, 'model': model, 'content': content, 'usage': {'input_tokens': 10, 'output_tokens': 5, 'cache_read_input_tokens': 100}}}


CLI_SESSION = [
    user('Make the landing page look better and more modern'),
    assistant('m1', 'model-big', ['Edit'] * 16),
    assistant('m1', 'model-big'),  # same message id streamed twice: must count once
    user('yes'),
    assistant('m2', 'model-big', ['Bash']),
    user('it is still broken, fix the header'),
    assistant('m3', 'model-small', ['Skill']),
    user('Here is my key sk-abcdefghijklmnopqrstuvwx and mail jane@example.com, call +420 123 456 789'),
    user([{'type': 'tool_result', 'content': 'tool output, not a prompt'}]),
    user('<command-name>/model</command-name>'),
    user('[Request interrupted by user]'),
    user('update?'),
    'this line is not json',
]

# Ordinary task prompts that must NOT trip the coarse signals.
PLAIN_PROMPTS = [
    'fix the login bug in auth.py',
    'update the README with the new install steps',
    'look at the logs and tell me why the job failed',
    'design the API for the billing service',
    'add a status endpoint that returns the build number',
    'write tests for the done callback',
    'rename the progress module to tracker',
    'check the coding style guide and apply it',
    'is the migration ready to run on staging',
    'make the report generator faster',
]

DESKTOP_SESSION = [
    user('Build the booking form. Done when a screenshot shows it working on mobile, see ./mock.png', cwd='/tmp/scratch-1',
         promptSource='sdk', origin={'kind': 'human'}, turnOrigin='human', permissionMode='plan'),
    {'type': 'relocated', 'relocatedCwd': '/work/booking', 'sessionId': 'x'},
    assistant('d1', 'model-big', ['Agent', 'ExitPlanMode']),
    user('scheduled run', promptSource='system', origin={'kind': 'task-notification'}, turnOrigin='scheduled'),
    user([{'type': 'text', 'text': 'this is what I see'}, {'type': 'image', 'source': {}}], promptSource='sdk', origin={'kind': 'human'}),
    user('subagent chatter', isSidechain=True),
]


def run(args, env=None):
    return subprocess.run([sys.executable, COLLECT] + args, capture_output=True, text=True, encoding='utf-8', env=env)


class CollectTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = cls.tmp.name
        cls.home = os.path.join(base, 'claude')
        proj = os.path.join(cls.home, 'projects')
        for name, records in (('-work-shop', CLI_SESSION), ('-tmp-scratch', DESKTOP_SESSION)):
            os.makedirs(os.path.join(proj, name))
            with open(os.path.join(proj, name, 'aaaaaaaa-' + name + '.jsonl'), 'w', encoding='utf-8') as fh:
                for r in records:
                    fh.write((r if isinstance(r, str) else json.dumps(r)) + '\n')
        os.makedirs(os.path.join(cls.home, 'skills', 'checker'))
        with open(os.path.join(cls.home, 'CLAUDE.md'), 'w', encoding='utf-8') as fh:
            fh.write('rule one\nrule two\n')
        with open(os.path.join(cls.home, 'settings.json'), 'w', encoding='utf-8') as fh:
            json.dump({'hooks': {'Stop': []}, 'permissions': {'allow': ['Bash(ls:*)']}}, fh)
        cls.out = os.path.join(base, 'out.json')
        cls.res = run(['--home', cls.home, '--out', cls.out])
        with open(cls.out, encoding='utf-8') as fh:
            cls.d = json.load(fh)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_runs(self):
        self.assertEqual(self.res.returncode, 0, self.res.stderr)
        self.assertIn('Audit data: 2 sessions, 7 prompts', self.res.stdout)

    def test_only_human_prompts_count(self):
        self.assertEqual(self.d['scope']['prompts'], 7)
        self.assertEqual(self.d['scope']['unreadable_lines'], 1)
        self.assertEqual(self.d['verification']['interruptions'], 1)
        self.assertEqual(self.d['tools']['slash_commands'], {'/model': 1})
        self.assertEqual(self.d['tools']['automated_messages'], {'scheduled': 1})

    def test_approvals_are_excluded_from_briefing(self):
        self.assertEqual(self.d['prompting']['approvals_excluded'], 1)

    def test_signals(self):
        p = self.d['prompting']
        self.assertEqual(p['vague_words'], {'better': 1, 'modern': 1})
        self.assertEqual(p['big_tasks'], 1)
        self.assertEqual(p['with_image'], 1)
        self.assertEqual(self.d['safety']['prompts_with_secret'], 1)
        self.assertGreater(self.d['verification']['possible_correction_rounds_pct'], 0)
        self.assertGreater(self.d['verification']['prompts_with_criteria_or_proof_request_pct'], 0)
        self.assertGreater(self.d['verification']['status_pings_pct'], 0)

    def test_plain_task_prompts_trip_no_signal(self):
        home = os.path.join(self.tmp.name, 'plain')
        os.makedirs(os.path.join(home, 'projects', '-work-api'))
        with open(os.path.join(home, 'projects', '-work-api', 'bbbbbbbb.jsonl'), 'w', encoding='utf-8') as fh:
            for i, text in enumerate(PLAIN_PROMPTS):
                fh.write(json.dumps(user(text)) + '\n' + json.dumps(assistant('p%d' % i, 'model-big', ['Edit'])) + '\n')
        out = os.path.join(self.tmp.name, 'plain.json')
        self.assertEqual(run(['--home', home, '--out', out, '--lang', 'en']).returncode, 0)
        with open(out, encoding='utf-8') as fh:
            d = json.load(fh)
        self.assertEqual(d['scope']['prompts'], len(PLAIN_PROMPTS))
        self.assertEqual(d['verification']['possible_correction_rounds_pct'], 0)
        self.assertEqual(d['verification']['status_pings_pct'], 0)
        self.assertEqual(d['prompting']['visual_prompts'], 0)
        self.assertEqual(d['prompting']['vague_words'], {})
        self.assertEqual(d['prompting']['approvals_excluded'], 0)

    def test_models_and_tools(self):
        self.assertEqual(self.d['models']['model-big']['responses'], 3)  # m1 once, m2, d1
        self.assertEqual(self.d['models']['model-small']['responses'], 1)
        self.assertEqual(self.d['tools']['skills_invoked'], {'checker': 1})
        self.assertEqual(self.d['tools']['sessions_with_plan'], 1)
        self.assertEqual(self.d['tools']['sessions_with_subagent'], 1)

    def test_relocated_session_is_not_left_in_temp(self):
        self.assertEqual(self.d['projects']['sessions_started_in_temp_pct'], 50.0)
        self.assertEqual(self.d['projects']['sessions_left_in_temp_pct'], 0)

    def test_setup(self):
        s = self.d['setup']
        self.assertEqual((s['global_claude_md_lines'], s['skills'], s['hooks'], s['allowed_commands']), (2, ['checker'], ['Stop'], 1))

    def test_samples_are_masked(self):
        blob = json.dumps(self.d['samples'])
        for leaked in ('sk-abcdefghijklmnopqrstuvwx', 'jane@example.com', '123 456 789'):
            self.assertNotIn(leaked, blob)
        self.assertIn('[SECRET]', blob)

    def test_no_samples_option(self):
        out = os.path.join(self.tmp.name, 'nosamples.json')
        self.assertEqual(run(['--home', self.home, '--out', out, '--samples', '0']).returncode, 0)
        with open(out, encoding='utf-8') as fh:
            self.assertEqual(json.load(fh)['samples'], [])

    def test_config_dir_env(self):
        out = os.path.join(self.tmp.name, 'env.json')
        env = dict(os.environ, CLAUDE_CONFIG_DIR=self.home)
        self.assertEqual(run(['--out', out], env=env).returncode, 0)

    def test_bad_input_exits_2(self):
        empty = os.path.join(self.tmp.name, 'empty')
        os.makedirs(os.path.join(empty, 'projects'))
        self.assertEqual(run(['--dir', os.path.join(self.tmp.name, 'missing')]).returncode, 2)
        self.assertEqual(run(['--home', empty, '--out', os.path.join(self.tmp.name, 'x.json')]).returncode, 2)
        self.assertEqual(run(['--home', self.home, '--lang', 'xx']).returncode, 2)


if __name__ == '__main__':
    unittest.main()
