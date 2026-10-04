"""Core unit tests: validator, evidence handling, audit arithmetic and mocked API logging."""
import unittest,json,tempfile,io
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from evidencematch import *
ROOT=Path(__file__).resolve().parents[0]
class Tests(unittest.TestCase):
 def setUp(self):
  self.e=build_evidence('I built a Python API for a student project.\nI assisted with testing.\n\nI created a Coze workflow prototype.')
  self.job={'jd_id':'TEST','text':'Python API development','cohort':'custom'}
  self.o={'requirements':[{'requirement_id':'R1','requirement_text':'Python API development','label':'Partial','citations':[{'evidence_id':'E001','quote':'I built a Python API for a student project.'}],'gap':'Production deployment not documented.'}], 'bullets':[{'claim_id':'B1','text':'Built a Python API for a student project.','citations':[{'evidence_id':'E001','quote':'I built a Python API for a student project.'}]}], 'abstain':False,'abstention_reason':'','scope_note':'One requirement.'}
 def test_valid(self):self.assertTrue(validate(self.o,self.e,self.job['text'])['ok'])
 def test_fake_id(self):
  self.o['bullets'][0]['citations'][0]['evidence_id']='E999';self.assertFalse(validate(self.o,self.e,self.job['text'])['ok'])
 def test_exact_quote(self):
  self.o['bullets'][0]['citations'][0]['quote']='I led a production team.';self.assertFalse(validate(self.o,self.e,self.job['text'])['ok'])
 def test_fabricated_metric(self):
  self.o['bullets'][0]['text']='Built a Python API improving speed by 40%.';self.assertIn('unsupported_number',validate(self.o,self.e,self.job['text'])['bullet_errors']['B1'])
 def test_hallucinated_requirement(self):
  self.o['requirements'][0]['requirement_text']='Must know Rust';self.assertFalse(validate(self.o,self.e,self.job['text'])['ok'])
 def test_missing_citation_is_allowed_only_for_missing(self):
  self.o['requirements'][0].update(label='Missing',citations=[]);self.assertTrue(validate(self.o,self.e,self.job['text'])['ok'])
 def test_malformed(self):
  for x in [None,[],{}, {'requirements':None,'bullets':None}]:self.assertFalse(validate(x,self.e,self.job['text'])['ok'])
 def test_abstention_not_zero_ucr(self):
  self.assertIsNone(audit_summary([],[])['ucr_complete'])
 def test_pending_audit_not_pass(self):
  r={'run_id':'r','status':'ready_for_human_review','output':self.o,'validation':{'bullet_errors':{'B1':[]}}}
  m=audit_summary([r],[]);self.assertEqual(m['pending_bullets'],1);self.assertIsNone(m['ucr_complete'])
  a=[{'run_id':'r','claim_id':'B1','verdict':'unclear'}];self.assertEqual(audit_summary([r],a)['ucr_complete'],1)
 def test_corpus_provenance(self):
  jobs=json.loads((ROOT/'jd_corpus_48.json').read_text()); new=jobs[18:]
  self.assertEqual(len(jobs),48);self.assertEqual(len({j['source_url'] for j in new}),30)
  self.assertTrue(all(j['source_content_sha256'] and j['gold_label'] is None for j in new))
  self.assertTrue(all(len(j['text'].split())<150 for j in new))
 def test_mocked_api_logs_usage_without_key(self):
  response={'id':'fixture','model':'openai/gpt-4o','choices':[{'message':{'content':json.dumps(self.o)},'finish_reason':'stop'}],'usage':{'prompt_tokens':100,'completion_tokens':200,'cost':0.00225}}
  model={'id':'openai/gpt-4o','context_length':128000,'pricing':{'prompt':'0.0000025','completion':'0.00001'},'supported_parameters':['response_format']}
  with tempfile.TemporaryDirectory() as temp,patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(response).encode())):
   r=match_job(self.job,self.e,'TEST_SECRET_NOT_REAL',model,temp)
   self.assertEqual(r['status'],'ready_for_human_review');self.assertEqual(r['cost_reported_usd'],0.00225)
   self.assertNotIn('TEST_SECRET_NOT_REAL',next(Path(temp).glob('*.json')).read_text())
 def test_truncated_output_blocked(self):
  data={'choices':[{'message':{'content':json.dumps(self.o)},'finish_reason':'length'}]}
  with tempfile.TemporaryDirectory() as temp,patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(data).encode())):
   r=match_job(self.job,self.e,'TEST_KEY',{'id':'test','context_length':128000},temp);self.assertEqual(r['status'],'failed')
 def test_http_failure_saved(self):
  with tempfile.TemporaryDirectory() as temp,patch('urllib.request.urlopen',side_effect=HTTPError('url',401,'Unauthorized',{},None)):
   r=match_job(self.job,self.e,'TEST_KEY',{'id':'test','context_length':128000},temp);self.assertEqual(r['status'],'failed');self.assertIn('401',r['error'])
 def test_text_resume(self):self.assertTrue(read_resume('resume.txt',('Candidate project experience. '*5).encode()))
 def test_empty_pdf_alternative(self):
  with self.assertRaises(ValueError):read_resume('scan.png',b'not_image')
if __name__=='__main__':unittest.main()
