"""Software tests only: the API is mocked, so nothing here measures model quality."""
import io, json, shutil, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import session
from evidencematch import build_evidence, redact_contacts, validate, bullet_warnings, PROMPT_VERSION
ROOT = Path(__file__).resolve().parents[0]
SAMPLE = (ROOT / 'sample_resume_synthetic.txt').read_text()

class Evidence(unittest.TestCase):
    def setUp(self):
        self.text, self.removed = redact_contacts(SAMPLE); self.ev = build_evidence(self.text)
    def test_contact_line_removed_dates_kept(self):
        self.assertEqual(self.removed, 1)
        blob = json.dumps(self.ev)
        self.assertNotIn('example.com', blob); self.assertNotIn('9123', blob); self.assertIn('2025.05', blob)
    def test_year_ranges_are_not_phone_numbers(self):
        self.assertEqual(redact_contacts('Studied 2021-2025 in Xi\'an')[1], 0)
    def test_units_follow_bullets_and_keep_context(self):
        kinds = [e['kind'] for e in self.ev]
        self.assertEqual(kinds.count('entry_heading'), 3); self.assertEqual(kinds.count('skills_list'), 1)
        unit = next(e for e in self.ev if 'unit tests' in e['text'])
        self.assertIn('Course FAQ chatbot', unit['entry']); self.assertEqual(unit['section'], 'Projects')
        self.assertNotIn('Alex Tan', json.dumps(self.ev))
    def test_wrapped_lines_rejoin(self):
        ev = build_evidence('项目经历\n• 构建多节点\n协作系统 using\nPython\n• 第二条\n• 第三条')
        self.assertEqual(ev[0]['text'], '构建多节点协作系统 using Python')
    def test_no_bullets_falls_back_to_paragraphs(self):
        self.assertEqual(build_evidence('I built an API.\nI tested it.\n\nSecond paragraph.')[0]['kind'], 'paragraph')
    def test_quote_check_ignores_whitespace_only(self):
        ev = build_evidence('项目经历\n• 构建多节点 协作系统并完成部署\n• 二二二二\n• 三三三三')
        def out(q): return {'requirements': [{'requirement_id': 'R1', 'requirement_text': 'Python', 'label': 'Missing', 'citations': [], 'gap': 'none'}],
                            'bullets': [{'claim_id': 'B1', 'text': 'Built a system.', 'citations': [{'evidence_id': 'E001', 'quote': q}]}],
                            'abstain': False, 'abstention_reason': '', 'scope_note': ''}
        self.assertTrue(validate(out('构建多节点协作系统'), ev, 'Python')['ok'])
        self.assertFalse(validate(out('构建多节点协同系统'), ev, 'Python')['ok'])

class Warnings(unittest.TestCase):
    def test_pilot_failure_patterns_are_flagged(self):
        intern = {'kind': 'bullet', 'entry': 'Intern'}; skills = {'kind': 'skills_list', 'entry': ''}
        self.assertIn('vague_intensifier', bullet_warnings('Achieved significant improvements.', [intern], ['评测集']))
        self.assertIn('ownership_upgrade', bullet_warnings('Led backend design.', [intern], ['协助模块化后端架构设计']))
        self.assertIn('skills_list_only', bullet_warnings('Experimented with RAG.', [skills], ['RAG']))
        self.assertIn('deployment_not_quoted', bullet_warnings('Developed and deployed APIs.', [intern], ['开发 RESTful API']))
        self.assertIn('merges_entries', bullet_warnings('Built X and Y.', [intern, {'kind': 'bullet', 'entry': 'Project'}], ['a', 'b']))
        self.assertEqual(bullet_warnings('Assisted backend design and deployment.', [intern], ['协助完成部署']), [])

class Session(unittest.TestCase):
    """Scripted end-to-end pass through upload, two mocked runs, audit, metrics and export."""
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        for f in ('jd_corpus_48.json', 'adversarial_jobs.json', 'eval_plan.json'): shutil.copy(ROOT / f, self.root / f)
    def tearDown(self): shutil.rmtree(self.root)
    def fake_open(self, req, timeout=0):
        url = req if isinstance(req, str) else req.full_url
        if url.endswith('/models'): return io.BytesIO(json.dumps({'data': [{'id': 'openai/gpt-4o', 'context_length': 128000, 'pricing': {'prompt': '0.0000025', 'completion': '0.00001'}, 'supported_parameters': ['response_format']}]}).encode())
        if url.endswith('/key'): return io.BytesIO(json.dumps({'data': {'usage': 0.1, 'limit': 5, 'limit_remaining': 4.9}}).encode())
        body = json.loads(req.data); user = json.loads(body['messages'][1]['content']); jd = user['job_description']
        self.assertNotIn('source', user['evidence'][0])
        unit = next(e for e in user['evidence'] if 'Flask endpoint' in e['text'])
        out = {'requirements': [{'requirement_id': 'R1', 'requirement_text': jd[:20], 'label': 'Strong', 'citations': [{'evidence_id': unit['evidence_id'], 'quote': unit['text'][:30]}], 'gap': ''},
                                {'requirement_id': 'R2', 'requirement_text': jd[20:45], 'label': 'Missing', 'citations': [], 'gap': 'No evidence supplied.'}],
               'bullets': [{'claim_id': 'B1', 'text': 'Wrote a Flask endpoint.', 'citations': [{'evidence_id': unit['evidence_id'], 'quote': unit['text'][:30]}]},
                           {'claim_id': 'B2', 'text': 'Led and deployed an advanced chatbot.', 'citations': [{'evidence_id': unit['evidence_id'], 'quote': unit['text'][:30]}]}],
               'abstain': False, 'abstention_reason': '', 'scope_note': 'fixture'}
        return io.BytesIO(json.dumps({'id': 'x', 'model': 'openai/gpt-4o', 'choices': [{'message': {'content': json.dumps(out)}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 10, 'completion_tokens': 10, 'cost': 0.01}}).encode())
    def script(self, answers):
        it = iter(answers)
        return lambda prompt='': next(it)
    def test_full_flow(self):
        KEY = 'sk-or-TEST_SECRET_NOT_REAL'
        with patch('urllib.request.urlopen', side_effect=self.fake_open), patch('builtins.print'):
            with self.assertRaises(ValueError): session.prepare_resume(self.root, 'cv.txt', SAMPLE.encode(), ask=self.script(['no']))
            session.prepare_resume(self.root, 'cv.txt', SAMPLE.encode(), ask=self.script(['YES']))
            self.assertEqual(session.run_jobs(self.root, ['JD19'], 'dev_regression', ask=self.script(['no']), secret=lambda p: KEY), [])
            self.assertEqual(len(session.run_jobs(self.root, ['JD19'], 'dev_regression', ask=self.script(['RUN']), secret=lambda p: KEY)), 1)
            self.assertEqual(session.run_jobs(self.root, ['JD19'], 'dev_regression', ask=self.script([]), secret=lambda p: KEY), [])  # not billed twice
            self.assertEqual(len(session.run_jobs(self.root, ['JD23', 'JD44'], 'heldout', ask=self.script(['RUN']), secret=lambda p: KEY)), 2)
            per_run = ['1', '1', '2', '2', 'model said Missing', '1', 'ok', '2', 'a', 'not led', '1', 'missed degree']
            session.audit(self.root, ask=self.script(per_run * 3))
            session.audit(self.root, ask=self.script([]))  # nothing left to ask
            dest, rep = session.export(self.root, include_evidence=False)
        for p in self.root.rglob('*'):
            if p.is_file() and p.suffix in {'.json', '.zip'}: self.assertNotIn(KEY.encode(), p.read_bytes())
        self.assertEqual(rep['prompt_version'], PROMPT_VERSION)
        self.assertEqual(rep['dev_regression']['jobs'], ['JD19']); self.assertEqual(rep['heldout']['jobs'], ['JD23', 'JD44'])
        h = rep['heldout']
        self.assertEqual(h['bullets']['generated'], 4); self.assertEqual(h['bullets']['ucr_conservative_unsupported_or_unclear'], 0.5)
        self.assertEqual(h['automatic_flags_vs_human'], {'flagged': 2, 'flagged_and_bad': 2, 'bad': 2, 'precision': 1.0, 'recall': 1.0})
        self.assertEqual(h['requirement_labels']['n'], 4); self.assertEqual(h['requirement_labels']['llm']['accuracy'], 0.5)
        self.assertEqual(h['requirement_labels']['llm_stricter_than_human'], 2)
        self.assertEqual(h['extraction']['missed_requirements_total'], 2); self.assertEqual(h['bullets']['failure_types'], {'ownership_or_seniority_inflated': 2})
        self.assertEqual(len(rep['heldout_jobs_planned_but_not_run']), 8)
        self.assertEqual(rep['adversarial_injection_probe'], {'run': False})
        import zipfile
        names = zipfile.ZipFile(dest).namelist()
        self.assertFalse(any('private' in n for n in names)); self.assertIn('results/evaluation_report.json', names)
    def test_injection_probe_is_reported_apart_from_heldout(self):
        with patch('urllib.request.urlopen', side_effect=self.fake_open), patch('builtins.print'):
            session.prepare_resume(self.root, 'cv.txt', SAMPLE.encode(), ask=self.script(['YES']))
            session.run_jobs(self.root, ['JD19', 'ADV01'], 'heldout', ask=self.script(['RUN']), secret=lambda p: 'k')
            rep = session.evaluation_report(self.root)
        probe = rep['adversarial_injection_probe']
        self.assertTrue(probe['run']); self.assertFalse(probe['all_labels_strong']); self.assertEqual(probe['strong_labels_on_clean_dev_job'], 1)
        self.assertEqual(rep['heldout']['jobs'], [])
    def test_unreviewed_bullets_give_no_rate(self):
        with patch('urllib.request.urlopen', side_effect=self.fake_open), patch('builtins.print'):
            session.prepare_resume(self.root, 'cv.txt', SAMPLE.encode(), ask=self.script(['YES']))
            session.run_jobs(self.root, ['JD23'], 'heldout', ask=self.script(['RUN']), secret=lambda p: 'k')
            rep = session.evaluation_report(self.root)
        self.assertIsNone(rep['heldout']['bullets']['ucr_conservative_unsupported_or_unclear']); self.assertEqual(rep['heldout']['bullets']['pending'], 2)
        self.assertIsNone(rep['dev_regression']['bullets']['ucr_conservative_unsupported_or_unclear'])

if __name__ == '__main__': unittest.main()
