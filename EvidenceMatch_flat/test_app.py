"""Backend tests through Flask's test client. The provider is mocked: these test the software, not the model."""
import io, json, shutil, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import app as webapp

KEY = 'sk-or-TEST_SECRET_NOT_REAL'

class App(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.patch = patch.object(webapp, 'RESULTS', self.tmp / 'results'); self.patch.start()
        self.load = patch.object(webapp, 'load_records', lambda root: webapp.__dict__['_records'](self.tmp)); 
        webapp._records = lambda tmp: [json.loads(p.read_text()) for p in sorted((tmp / 'results').glob('2*.json'))]
        self.load.start(); self.c = webapp.app.test_client()
        self.ev = self.c.post('/api/resume', json={'sample': True}).get_json()['evidence']
    def tearDown(self):
        self.patch.stop(); self.load.stop(); shutil.rmtree(self.tmp)
    def fake(self, req, timeout=0):
        url = req if isinstance(req, str) else req.full_url
        if url.endswith('/models'): return io.BytesIO(json.dumps({'data': [webapp.GPT4O_INFO]}).encode())
        self.assertEqual(req.headers['Authorization'], 'Bearer ' + KEY)
        fixture = json.loads((webapp.ROOT / 'demo_fixture_response.json').read_text()); fixture['usage'] = {'prompt_tokens': 10, 'completion_tokens': 5, 'cost': 0.02}
        return io.BytesIO(json.dumps(fixture).encode())
    def test_resume_upload_redacts_and_rejects(self):
        import base64
        r = self.c.post('/api/resume', json={'filename': 'cv.txt', 'content_b64': base64.b64encode((webapp.ROOT / 'sample_resume_synthetic.txt').read_bytes()).decode()}).get_json()
        self.assertEqual(r['contact_lines_removed'], 1); self.assertNotIn('example.com', json.dumps(r))
        self.assertEqual(self.c.post('/api/resume', json={'filename': 'cv.png', 'content_b64': 'aGk='}).status_code, 400)
    def test_match_needs_key_or_demo(self):
        self.assertEqual(self.c.post('/api/match', json={'evidence': self.ev, 'jd_id': 'JD19'}).status_code, 400)
        self.assertEqual(self.c.post('/api/match', json={'evidence': [], 'jd_id': 'JD19', 'offline_demo': True}).status_code, 400)
    def test_live_path_keeps_key_out_of_files_and_response(self):
        with patch('urllib.request.urlopen', side_effect=self.fake):
            r = self.c.post('/api/match', json={'evidence': self.ev, 'jd_id': 'JD19'}, headers={'X-OpenRouter-Key': KEY})
        rec = r.get_json(); self.assertEqual(rec['status'], 'ready_for_human_review'); self.assertEqual(rec['cost_reported_usd'], 0.02)
        self.assertNotIn(KEY, r.get_data(as_text=True))
        for p in self.tmp.rglob('*'):
            if p.is_file(): self.assertNotIn(KEY, p.read_text())
    def test_custom_job_text_is_validated_against_itself(self):
        with patch('urllib.request.urlopen', side_effect=self.fake):
            rec = self.c.post('/api/match', json={'evidence': self.ev, 'job_text': 'We need someone to prepare data and write Python services for our team.'}, headers={'X-OpenRouter-Key': KEY}).get_json()
        self.assertEqual(rec['status'], 'blocked_validation')   # the canned requirement texts are not in this posting
    def test_offline_demo_review_and_metrics_stay_separate(self):
        rec = self.c.post('/api/match', json={'evidence': self.ev, 'jd_id': 'JD19', 'offline_demo': True}).get_json()
        self.assertEqual(rec['runner'], 'offline_fixture'); self.assertIn('ownership_upgrade', rec['validation']['bullet_warnings']['B3'])
        bad = self.c.post('/api/review', json={'run_id': rec['run_id'], 'evidence': self.ev, 'bullets': [{'claim_id': 'B1'}]})
        self.assertEqual(bad.status_code, 400)
        review = {'run_id': rec['run_id'], 'evidence': self.ev, 'requirements': [{'requirement_id': 'R4', 'requirement_text': 'prepare data', 'human_label': 'Partial', 'model_label': 'Strong'}],
                  'bullets': [{'claim_id': 'B1', 'verdict': 'supported'}, {'claim_id': 'B2', 'verdict': 'supported'},
                              {'claim_id': 'B3', 'verdict': 'unsupported', 'failure_type': 'ownership_or_seniority_inflated', 'notes': 'Supported, not led.'}]}
        m = self.c.post('/api/review', json=review).get_json(); m = self.c.post('/api/review', json=review).get_json()   # saving twice must not double count
        demo = m['offline_demo_runs']
        self.assertEqual(m['live_runs']['attempted_runs'], 0); self.assertEqual(demo['bullets']['reviewed'], 3)
        self.assertAlmostEqual(demo['bullets']['ucr_conservative_unsupported_or_unclear'], 1 / 3)
        self.assertEqual(demo['automatic_flags_vs_human']['recall'], 1.0); self.assertEqual(demo['requirement_labels']['llm_more_generous_than_human'], 1)
    def test_pages_and_recorded_evaluation(self):
        self.assertIn(b'EvidenceMatch', self.c.get('/').data); self.assertEqual(len(self.c.get('/api/jobs').get_json()), 49)
        self.assertEqual(self.c.get('/api/evaluation').get_json()['heldout']['bullets']['reviewed'], 15)

if __name__ == '__main__': unittest.main()
