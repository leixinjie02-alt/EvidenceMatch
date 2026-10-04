"""EvidenceMatch local web app. Run:  python app.py   then open http://127.0.0.1:8000

Backend: this file (Flask) + evidencematch.py + session.py. Frontend: index.html.
All files sit in one folder on purpose, so the repository can be uploaded through the GitHub web page.
The server keeps no résumé and no API key in memory between requests: the browser holds the confirmed
evidence and sends the key in a header for the one call that needs it. Run records go to results/ (git-ignored)."""
import base64, json
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from evidencematch import (GPT4O_INFO, PROMPT_VERSION, apply_response, build_evidence, digest, fetch_models,
                               match_job, new_record, read_resume, redact_contacts, save_record)
from session import MODEL_ID, _load, _save, all_jobs, load_records, split_metrics

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / 'results'
app = Flask(__name__, static_folder=None)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

class BadRequest(Exception): pass

@app.errorhandler(BadRequest)
@app.errorhandler(ValueError)
def bad_request(e): return jsonify(error=str(e)), 400

def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict): raise BadRequest('Expected a JSON object.')
    return data

def clean_evidence(raw):
    """Accept only the fields the pipeline uses, so a client cannot smuggle anything else into the prompt."""
    if not isinstance(raw, list) or not raw or len(raw) > 400: raise BadRequest('Confirm a résumé first.')
    keys = ('evidence_id', 'section', 'entry', 'kind', 'text', 'source')
    out = [{k: str(e.get(k, '')) for k in keys} for e in raw if isinstance(e, dict)]
    if len(out) != len(raw) or any(not e['evidence_id'] or not e['text'] for e in out): raise BadRequest('Malformed evidence.')
    return out

@app.get('/')
def index(): return send_from_directory(ROOT, 'index.html')

@app.get('/api/info')
def info(): return jsonify(prompt_version=PROMPT_VERSION, model=MODEL_ID)

@app.get('/api/jobs')
def jobs():
    return jsonify([{'jd_id': j['jd_id'], 'title': ' · '.join(filter(None, [j.get('company'), j.get('title')])) or j['text'][:28],
                     'cohort': j.get('cohort'), 'text': j['text'], 'source_url': j.get('source_url')} for j in all_jobs(ROOT).values()])

@app.post('/api/resume')
def resume():
    data = body()
    if data.get('sample'):
        name, content = 'sample_resume_synthetic.txt', (ROOT / 'sample_resume_synthetic.txt').read_bytes()
    else:
        try: name, content = str(data['filename']), base64.b64decode(data['content_b64'], validate=True)
        except Exception: raise BadRequest('Send filename and content_b64.')
    text, removed = redact_contacts(read_resume(name, content))
    return jsonify(evidence=build_evidence(text), contact_lines_removed=removed, filename=name)

@app.post('/api/match')
def match():
    data = body(); evidence = clean_evidence(data.get('evidence')); known = all_jobs(ROOT)
    if data.get('jd_id') in known: job = known[data['jd_id']]
    else:
        text = str(data.get('job_text', '')).strip()
        if len(text) < 40 or len(text) > 12000: raise BadRequest('Paste a job description of 40 to 12,000 characters, or pick one from the list.')
        job = {'jd_id': 'CUSTOM', 'text': text, 'cohort': 'custom', 'representation': 'user_pasted_text'}
    if data.get('offline_demo'):
        # Hand-written canned response, pushed through the real validator. Never presented as model output.
        record = new_record(job, evidence, GPT4O_INFO, 'offline_demo', runner='offline_fixture'); record['latency_seconds'] = 0.0
        try: apply_response(record, _load(ROOT / 'demo_fixture_response.json', {}), job, evidence, GPT4O_INFO)
        except (ValueError, KeyError, TypeError, IndexError) as e: record['error'] = type(e).__name__ + ': ' + str(e)[:200]
        record.update(cost_reported_usd=None, cost_estimate_usd=None, requested_model='offline-fixture')
        return jsonify(save_record(record, RESULTS))
    key = request.headers.get('X-OpenRouter-Key', '').strip()
    if not key: raise BadRequest('Enter your OpenRouter API key, or use the offline demo.')
    try: model = fetch_models()[MODEL_ID]
    except Exception: model = GPT4O_INFO          # catalogue unreachable: fall back to the recorded price snapshot
    return jsonify(match_job(job, evidence, key, model, RESULTS, run_label='app'))

@app.post('/api/review')
def review():
    """Store the human verdicts for one run. A later save for the same run replaces the earlier one."""
    data = body(); run_id = str(data.get('run_id', ''))
    record = next((r for r in load_records(ROOT) if r['run_id'] == run_id), None)
    if not record: raise BadRequest('Unknown run.')
    bullets, reqs = data.get('bullets') or [], data.get('requirements') or []
    for b in bullets:
        if b.get('verdict') not in {'supported', 'unsupported', 'unclear'}: raise BadRequest('Every bullet needs a verdict.')
    for r in reqs:
        if r.get('human_label') not in {'Strong', 'Partial', 'Missing'}: raise BadRequest('Every reviewed requirement needs a label.')
    def replace(path, rows):
        _save(path, [a for a in _load(path, []) if a.get('run_id') != run_id] + rows)
    replace(RESULTS / 'human_audit.json', [{'run_id': run_id, 'jd_id': record['jd_id'], 'claim_id': str(b['claim_id']), 'verdict': b['verdict'],
        'failure_type': b.get('failure_type') or None, 'notes': str(b.get('notes', ''))[:500], 'reviewer': 'user',
        'accepted': b['verdict'] == 'supported' and record['status'] == 'ready_for_human_review'} for b in bullets])
    replace(RESULTS / 'requirement_audit.json', [{'run_id': run_id, 'jd_id': record['jd_id'], 'requirement_id': str(r['requirement_id']),
        'requirement_text': str(r.get('requirement_text', '')), 'human_label': r['human_label'], 'model_label': r.get('model_label'),
        'citation_relevant': None, 'notes': str(r.get('notes', ''))[:500], 'model_label_visible': True,
        'human_label_entered_before_model_label_shown': False, 'reviewer': 'user'} for r in reqs])
    return metrics_for(clean_evidence(data.get('evidence')))

def metrics_for(evidence):
    ehash = digest(evidence)
    records = [r for r in load_records(ROOT) if r.get('evidence_hash') == ehash and r.get('prompt_version') == PROMPT_VERSION]
    live = [r for r in records if r.get('runner') != 'offline_fixture']
    m = split_metrics(live, _load(RESULTS / 'human_audit.json', []), _load(RESULTS / 'requirement_audit.json', []), [], evidence)
    demo = split_metrics([r for r in records if r.get('runner') == 'offline_fixture'], _load(RESULTS / 'human_audit.json', []),
                         _load(RESULTS / 'requirement_audit.json', []), [], evidence)
    return jsonify(live_runs=m, offline_demo_runs=demo, note='Offline demo runs use a canned response and are never mixed into the live figures.')

@app.post('/api/metrics')
def metrics(): return metrics_for(clean_evidence(body().get('evidence')))

@app.get('/api/evaluation')
def evaluation():
    """The author's recorded v2.3 evaluation, read from the committed run_v23_* files."""
    return jsonify(_load(ROOT / 'run_v23_evaluation_report.json', {}))

if __name__ == '__main__':
    print('EvidenceMatch is running. Open http://127.0.0.1:8000 in your browser. Press Ctrl+C to stop.')
    app.run(host='127.0.0.1', port=8000, debug=False)
