"""Build a single-file browser page that sends the exact same requests as the Python runner and collects the human audit.
Usage: python build_browser_runner.py path/to/resume.pdf
The page embeds the confirmed (contact-free) evidence, so it is written to private/ and must not be committed."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[0]
sys.path.insert(0, str(ROOT))
from evidencematch import GPT4O_INFO, PROMPT_VERSION, build_evidence, build_payload, digest, read_resume, redact_contacts
from session import all_jobs

resume = Path(sys.argv[1])
text, removed = redact_contacts(read_resume(resume.name, resume.read_bytes()))
evidence = build_evidence(text)
plan = json.loads((ROOT / 'eval_plan.json').read_text())
jobs = all_jobs(ROOT)
order = plan['dev_regression'] + plan['heldout'] + plan['adversarial']
data = {'prompt_version': PROMPT_VERSION, 'evidence_hash': digest(evidence),
        'evidence': [{k: e[k] for k in ('evidence_id', 'section', 'entry', 'kind', 'text')} for e in evidence],
        'jobs': [{'jd_id': i, 'title': ' '.join(filter(None, [jobs[i].get('company'), jobs[i].get('title')])), 'text': jobs[i]['text'],
                  'payload': build_payload(jobs[i], evidence, GPT4O_INFO)} for i in order]}
html = (ROOT / 'runner_template.html').read_text(encoding='utf-8').replace('/*__DATA__*/null', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))
(ROOT / 'private').mkdir(exist_ok=True)
(ROOT / 'private/confirmed_evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
(ROOT / 'private/EvidenceMatch_Runner.html').write_text(html, encoding='utf-8')
print(f'{removed} contact line(s) removed; {len(evidence)} evidence units; {len(order)} jobs -> private/EvidenceMatch_Runner.html')
