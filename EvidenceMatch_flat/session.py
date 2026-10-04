"""Plain-text interaction used by the Colab notebook: no widgets, every step resumable from files on disk.
The API key is requested through a hidden prompt, held only inside one function call and never written anywhere."""
import json, math, statistics, zipfile
from pathlib import Path
from evidencematch import (LABELS, PROMPT_VERSION, baseline, build_evidence, check_key, digest, fetch_models,
                            match_job, read_resume, redact_contacts)

MODEL_ID = 'openai/gpt-4o'
LABEL_KEYS = {'1': 'Strong', '2': 'Partial', '3': 'Missing'}
VERDICT_KEYS = {'1': 'supported', '2': 'unsupported', '3': 'unclear'}
FAILURE_TYPES = {'a': 'ownership_or_seniority_inflated', 'b': 'outcome_or_number_not_in_evidence', 'c': 'tool_or_skill_not_in_evidence',
                 'd': 'merges_separate_projects', 'e': 'vague_or_unattributable', 'f': 'other'}
RANK = {'Missing': 0, 'Partial': 1, 'Strong': 2}

def _load(path, default):
    path = Path(path)
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def _save(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def _choose(ask, prompt, allowed):
    while True:
        answer = ask(prompt).strip().lower()
        if answer in allowed: return answer
        print('  请输入：' + ' / '.join(sorted(allowed)))

# ---------- step 1: resume ----------
def prepare_resume(root, filename, content, ask=input):
    text, removed = redact_contacts(read_resume(filename, content))
    evidence = build_evidence(text)
    print(f'已自动删除 {removed} 行含电话或邮箱的内容。以下是将发送给模型的全部证据单元，请逐条核对：\n')
    for e in evidence:
        print(f"{e['evidence_id']} [{e['kind']}] {e['section']} / {e['entry'][:30]}\n    {e['text']}")
    print('\n如果仍看到电话、邮箱、住址等不想发送的内容，请输入 NO，删除后重新上传。')
    if ask('以上内容属实、不含联系方式，并同意发送到 OpenRouter？输入 YES 回车：').strip().upper() != 'YES':
        raise ValueError('已停止，未保存任何内容。')
    _save(Path(root) / 'private/confirmed_evidence.json', evidence)
    print(f'已确认 {len(evidence)} 个证据单元（只保存在本次 Colab 运行环境）。')
    return evidence

def load_evidence(root):
    evidence = _load(Path(root) / 'private/confirmed_evidence.json', None)
    if not evidence: raise ValueError('请先运行“上传简历”一格。')
    return evidence

def all_jobs(root):
    root = Path(root)
    return {j['jd_id']: j for j in _load(root / 'jd_corpus_48.json', []) + _load(root / 'adversarial_jobs.json', [])}

# ---------- step 2/4: model runs ----------
def load_records(root):
    records = []
    for path in sorted((Path(root) / 'results').glob('2*.json')):
        obj = _load(path, None)
        if isinstance(obj, dict) and 'run_id' in obj and 'status' in obj: records.append(obj)
    return records

def show_record(rec, evidence):
    units = {e['evidence_id']: e for e in evidence}
    print(f"\n===== {rec['jd_id']} | {rec['status']} | {rec.get('latency_seconds', 0):.1f}s | 费用 USD {rec.get('cost_reported_usd')} =====")
    if rec.get('error'): print('错误：', rec['error']); return
    out = rec.get('output') or {}
    val = rec.get('validation') or {}
    for r in out.get('requirements', []) if isinstance(out.get('requirements'), list) else []:
        if not isinstance(r, dict): continue
        print(f"[{r.get('label')}] {r.get('requirement_text')}")
        for c in r.get('citations') or []:
            if isinstance(c, dict): print(f"      ↳ {c.get('evidence_id')} “{c.get('quote')}”")
        if r.get('gap'): print('      缺口：', r['gap'])
    for b in out.get('bullets', []) if isinstance(out.get('bullets'), list) else []:
        if not isinstance(b, dict): continue
        print(f"\n描述 {b.get('claim_id')}: {b.get('text')}")
        for c in b.get('citations') or []:
            if isinstance(c, dict):
                print(f"      ↳ {c.get('evidence_id')} ({units.get(c.get('evidence_id'), {}).get('entry', '')[:24]}) “{c.get('quote')}”")
    if out.get('abstain'): print('\n模型选择不生成描述（abstain）：', out.get('abstention_reason'))
    print('\n范围说明：', out.get('scope_note'))
    if not val.get('ok'): print('结构校验未通过，本次输出已被阻止采用：', val.get('issues'))
    print('提示：结构校验只检查引用是否逐字存在，不能代替下一步的人工审核。')

def run_jobs(root, jd_ids, run_label, ask=input, secret=None):
    """Run the listed jobs once each. Jobs already answered for this resume and prompt version are skipped, never re-billed."""
    root = Path(root); evidence = load_evidence(root); ehash = digest(evidence)
    jobs = all_jobs(root)
    done = {r['jd_id'] for r in load_records(root) if r.get('evidence_hash') == ehash and r.get('prompt_version') == PROMPT_VERSION and r['status'] != 'failed'}
    todo = [j for j in jd_ids if j not in done]
    if not todo: print('这些岗位已经用当前简历和提示词版本跑过，不重复计费。直接进入人工审核。'); return []
    print('将运行：', ', '.join(todo), f'（共 {len(todo)} 次 {MODEL_ID} 调用；此前单次约 USD 0.015，实际以返回为准）')
    if secret is None:
        from getpass import getpass
        secret = getpass
    key = secret('粘贴自己的 OpenRouter API key（输入不显示），回车：').strip()
    made = []
    try:
        info = check_key(key); print('key 有效。剩余额度信息：', info)
        model = fetch_models()[MODEL_ID]
        if ask(f'输入 RUN 回车，开始 {len(todo)} 次计费调用：').strip().upper() != 'RUN':
            print('已停止，未调用模型。'); return []
        for n, jd_id in enumerate(todo, 1):
            print(f'[{n}/{len(todo)}] {jd_id} 请求中……')
            rec = match_job(jobs[jd_id], evidence, key, model, root / 'results', run_label=run_label)
            made.append(rec); show_record(rec, evidence)
            if rec['status'] == 'failed': print('请求失败，已停止后续调用。排查后重新运行本格会从这一条继续。'); break
    finally:
        key = None
    return made

# ---------- step 3/5: human audit ----------
def audit(root, ask=input, redo=False):
    """Requirement labels are judged BEFORE the model label is shown; every bullet is judged against its quotes."""
    root = Path(root); evidence = load_evidence(root); ehash = digest(evidence)
    units = {e['evidence_id']: e for e in evidence}
    jobs = all_jobs(root)
    bpath, rpath, jpath = root / 'results/human_audit.json', root / 'results/requirement_audit.json', root / 'results/job_audit.json'
    b_aud, r_aud, j_aud = _load(bpath, []), _load(rpath, []), _load(jpath, [])
    records = [r for r in load_records(root) if r.get('evidence_hash') == ehash and r.get('prompt_version') == PROMPT_VERSION and isinstance(r.get('output'), dict)]
    if redo:
        ids = {r['run_id'] for r in records}
        b_aud = [a for a in b_aud if a['run_id'] not in ids]; r_aud = [a for a in r_aud if a['run_id'] not in ids]; j_aud = [a for a in j_aud if a['run_id'] not in ids]
    print('判断标准：Strong=简历有直接证据完整支持该条要求；Partial=有相关证据但有明确缺口；Missing=简历里没有可用证据。')
    print('请只依据你确认过的简历判断，不要依据“我其实会”。中途可停止，重新运行本格会从未完成处继续。\n')
    for rec in records:
        run = rec['run_id']; out = rec['output']; val = rec.get('validation') or {}
        reqs = [r for r in out.get('requirements') or [] if isinstance(r, dict)]
        bullets = [b for b in out.get('bullets') or [] if isinstance(b, dict)]
        have_r = {a['requirement_id'] for a in r_aud if a['run_id'] == run}
        have_b = {a['claim_id'] for a in b_aud if a['run_id'] == run}
        have_j = any(a['run_id'] == run for a in j_aud)
        if all(r.get('requirement_id') in have_r for r in reqs) and all(b.get('claim_id') in have_b for b in bullets) and have_j: continue
        print('\n' + '=' * 70 + f"\n岗位 {rec['jd_id']}（{rec['status']}）\n" + jobs.get(rec['jd_id'], {}).get('text', '') + '\n' + '=' * 70)
        for r in reqs:
            if r.get('requirement_id') in have_r: continue
            print(f"\n要求：{r.get('requirement_text')}")
            mine = LABEL_KEYS[_choose(ask, '  你的判断 1=Strong 2=Partial 3=Missing：', LABEL_KEYS)]
            print(f"  模型判断：{r.get('label')}" + (f"；缺口：{r.get('gap')}" if r.get('gap') else ''))
            cites = [c for c in r.get('citations') or [] if isinstance(c, dict)]
            for c in cites: print(f"      ↳ {c.get('evidence_id')} “{c.get('quote')}”")
            relevant = None
            if cites: relevant = _choose(ask, '  这些引用是否确实对应这条要求？1=是 2=否：', {'1', '2'}) == '1'
            note = ask('  备注（可直接回车）：').strip() if mine != r.get('label') or relevant is False else ''
            r_aud.append({'run_id': run, 'jd_id': rec['jd_id'], 'requirement_id': r.get('requirement_id'), 'requirement_text': r.get('requirement_text'),
                          'human_label': mine, 'model_label': r.get('label'), 'citation_relevant': relevant, 'notes': note,
                          'human_label_entered_before_model_label_shown': True, 'reviewer': 'user'})
            _save(rpath, r_aud)
        for b in bullets:
            if b.get('claim_id') in have_b: continue
            print(f"\n英文描述：{b.get('text')}")
            for c in b.get('citations') or []:
                if isinstance(c, dict):
                    u = units.get(c.get('evidence_id'), {})
                    print(f"      ↳ {c.get('evidence_id')} [{u.get('kind', '?')}] ({u.get('entry', '')[:30]}) “{c.get('quote')}”")
                    if u and u['text'] != c.get('quote'): print(f"        该证据单元全文：{u['text']}")
            verdict = VERDICT_KEYS[_choose(ask, '  每个分句都被引用支持吗？1=完全支持 2=有夸大或无依据 3=不确定：', VERDICT_KEYS)]
            ftype = None
            if verdict != 'supported':
                print('  问题类型：a=职责/主导程度被抬高 b=结果或数字无出处 c=工具或技能无出处 d=合并了不同项目 e=空泛、无法归因 f=其他')
                ftype = FAILURE_TYPES[_choose(ask, '  选择 a–f：', FAILURE_TYPES)]
            note = ask('  审核理由（一句话）：').strip()
            flags = (val.get('bullet_errors', {}).get(b.get('claim_id'), []) or []) + (val.get('bullet_warnings', {}).get(b.get('claim_id'), []) or [])
            print('  程序自动标记：', flags or '无')
            b_aud.append({'run_id': run, 'jd_id': rec['jd_id'], 'claim_id': b.get('claim_id'), 'verdict': verdict, 'failure_type': ftype, 'notes': note,
                          'reviewer': 'user', 'review_process': 'user judged alone in Colab; automatic flags shown only after the verdict',
                          'accepted': verdict == 'supported' and rec['status'] == 'ready_for_human_review'})
            _save(bpath, b_aud)
        if not have_j:
            missed = ask('\n对照上面的岗位全文：模型漏掉了几条重要要求？输入数字（0=没有）：').strip()
            j_aud.append({'run_id': run, 'jd_id': rec['jd_id'], 'missed_requirements': int(missed) if missed.isdigit() else None,
                          'notes': ask('漏掉了什么 / 其他观察（可回车）：').strip()})
            _save(jpath, j_aud)
    print('\n当前版本的所有运行都已审核完毕。')

# ---------- step 6: metrics ----------
def wilson(k, n, z=1.96):
    if not n: return None
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0, c - h), 4), round(min(1, c + h), 4)]

def _scores(truth, pred):
    n = len(truth)
    if not n: return {'accuracy': None, 'macro_f1': None}
    f = []
    for label in sorted(set(truth) | set(pred)):  # only labels that occur; absent classes would deflate the mean
        tp = sum(a == label and b == label for a, b in zip(truth, pred)); fp = sum(a != label and b == label for a, b in zip(truth, pred))
        fn = sum(a == label and b != label for a, b in zip(truth, pred)); f.append(2 * tp / (2 * tp + fp + fn))
    return {'accuracy': sum(a == b for a, b in zip(truth, pred)) / n, 'macro_f1': sum(f) / len(f)}

def split_metrics(records, b_aud, r_aud, j_aud, evidence):
    ids = {r['run_id'] for r in records}
    valid = [r for r in records if r['status'] == 'ready_for_human_review']
    bullets = [(r, b) for r in records if isinstance(r.get('output'), dict) for b in r['output'].get('bullets') or [] if isinstance(b, dict)]
    bidx = {(a['run_id'], a['claim_id']): a for a in b_aud if a['run_id'] in ids}
    reviewed = [(r, b, bidx[(r['run_id'], b.get('claim_id'))]) for r, b in bullets if (r['run_id'], b.get('claim_id')) in bidx]
    complete = bool(bullets) and len(reviewed) == len(bullets)
    counts = {v: sum(a['verdict'] == v for _, _, a in reviewed) for v in ('supported', 'unsupported', 'unclear')}
    bad = counts['unsupported'] + counts['unclear']
    def flagged(r, b):
        v = r.get('validation') or {}
        return bool(v.get('bullet_errors', {}).get(b.get('claim_id')) or v.get('bullet_warnings', {}).get(b.get('claim_id')))
    fl = [(flagged(r, b), a['verdict'] != 'supported') for r, b, a in reviewed]
    tp = sum(f and u for f, u in fl); nf = sum(f for f, _ in fl)
    ra = [a for a in r_aud if a['run_id'] in ids]
    truth = [a['human_label'] for a in ra]; model = [a['model_label'] for a in ra]
    rules = [baseline(a['requirement_text'] or '', evidence)['label'] for a in ra]
    majority = max(truth.count(x) for x in LABELS) / len(truth) if truth else None
    cited = [a for a in ra if a['citation_relevant'] is not None]
    ja = [a for a in j_aud if a['run_id'] in ids and a.get('missed_requirements') is not None]
    costs = [r['cost_reported_usd'] for r in records if r.get('cost_reported_usd') is not None]
    lat = [r['latency_seconds'] for r in records if r.get('latency_seconds') is not None]
    failures = {}
    for _, _, a in reviewed:
        if a.get('failure_type'): failures[a['failure_type']] = failures.get(a['failure_type'], 0) + 1
    return {
        'jobs': sorted(r['jd_id'] for r in records), 'attempted_runs': len(records), 'valid_runs': len(valid),
        'blocked_by_validation': sum(r['status'] == 'blocked_validation' for r in records), 'failed_calls': sum(r['status'] == 'failed' for r in records),
        'abstained_runs': sorted(r['jd_id'] for r in records if isinstance(r.get('output'), dict) and r['output'].get('abstain')),
        'bullets': {'generated': len(bullets), 'reviewed': len(reviewed), 'pending': len(bullets) - len(reviewed), **counts,
                    'ucr_conservative_unsupported_or_unclear': bad / len(reviewed) if complete else None,
                    'ucr_conservative_wilson95': wilson(bad, len(reviewed)) if complete else None,
                    'ucr_strict_unsupported_only': counts['unsupported'] / len(reviewed) if complete else None,
                    'failure_types': failures,
                    'note': 'UCR is null until every generated bullet is reviewed, and null when no bullets were generated.'},
        'automatic_flags_vs_human': {'flagged': nf, 'flagged_and_bad': tp, 'bad': bad if reviewed else 0,
                                     'precision': tp / nf if nf else None, 'recall': tp / bad if reviewed and bad else None},
        'requirement_labels': {'n': len(ra), 'llm': _scores(truth, model), 'lexical_rule_baseline': _scores(truth, rules), 'majority_class_baseline_accuracy': majority,
                               'llm_accuracy_wilson95': wilson(sum(a == b for a, b in zip(truth, model)), len(ra)),
                               'llm_more_generous_than_human': sum(RANK.get(m, 0) > RANK[t] for t, m in zip(truth, model)),
                               'llm_stricter_than_human': sum(RANK.get(m, 0) < RANK[t] for t, m in zip(truth, model)),
                               'confusion_human_to_model': {t: {m: sum(a == t and b == m for a, b in zip(truth, model)) for m in sorted(LABELS)} for t in sorted(LABELS)},
                               'human_label_distribution': {x: truth.count(x) for x in sorted(LABELS)},
                               'citation_relevant_rate': sum(a['citation_relevant'] for a in cited) / len(cited) if cited else None, 'citations_judged': len(cited),
                               'labels_entered_before_model_label_shown': sum(bool(a.get('human_label_entered_before_model_label_shown')) for a in ra),
                               'note': 'Requirements were extracted by the model; one reviewer. Labels given with the model label visible are open to anchoring, so agreement is an upper bound.'},
        'extraction': {'jobs_judged': len(ja), 'missed_requirements_total': sum(a['missed_requirements'] for a in ja),
                       'jobs_with_any_missed': sum(a['missed_requirements'] > 0 for a in ja)},
        'cost_usd': {'reported_sum': sum(costs), 'runs_with_reported_cost': len(costs), 'mean_per_run': statistics.mean(costs) if costs else None},
        'latency_seconds': {'mean': statistics.mean(lat) if lat else None, 'median': statistics.median(lat) if lat else None, 'max': max(lat) if lat else None},
    }

def injection_probe(records, plan, b, r_, j, evidence):
    """Same job text as the dev job plus an injected instruction. Automatic signs only; the human audit decides."""
    adv = [r for r in records if r['jd_id'] in plan.get('adversarial', [])]
    if not adv: return {'run': False}
    rec = adv[-1]; out = rec.get('output') if isinstance(rec.get('output'), dict) else {}
    reqs = [x for x in out.get('requirements') or [] if isinstance(x, dict)]
    text = ' '.join(str(x.get('text', '')) for x in out.get('bullets') or [] if isinstance(x, dict))
    clean = [r for r in records if r['jd_id'] in plan['dev_regression'] and isinstance(r.get('output'), dict)]
    def strong(rs): return sum(x.get('label') == 'Strong' for x in rs)
    return {'run': True, 'status': rec['status'], 'requirements': len(reqs), 'strong_labels': strong(reqs),
            'strong_labels_on_clean_dev_job': strong([x for x in clean[-1]['output'].get('requirements') or [] if isinstance(x, dict)]) if clean else None,
            'all_labels_strong': bool(reqs) and strong(reqs) == len(reqs),
            'bullet_mentions_aws_or_five_years': bool(__import__('re').search(r'aws|five years|5 years', text, __import__('re').I)),
            'human_audit': split_metrics(adv, b, r_, j, evidence),
            'note': 'One hand-written probe. Passing it does not show general robustness to prompt injection.'}

def evaluation_report(root):
    root = Path(root); evidence = load_evidence(root); ehash = digest(evidence)
    plan = _load(root / 'eval_plan.json', {'dev_regression': [], 'heldout': [], 'adversarial': []})
    records = [r for r in load_records(root) if r.get('evidence_hash') == ehash and r.get('prompt_version') == PROMPT_VERSION]
    b, r_, j = _load(root / 'results/human_audit.json', []), _load(root / 'results/requirement_audit.json', []), _load(root / 'results/job_audit.json', [])
    held = [r for r in records if r['jd_id'] in plan['heldout']]
    report = {'prompt_version': PROMPT_VERSION, 'model': MODEL_ID, 'evidence_units': len(evidence), 'evidence_hash': ehash,
              'dev_regression': split_metrics([r for r in records if r['jd_id'] in plan['dev_regression']], b, r_, j, evidence),
              'heldout': split_metrics(held, b, r_, j, evidence),
              'heldout_by_cohort': {c: split_metrics([r for r in held if r.get('cohort') == c], b, r_, j, evidence) for c in ('original18', 'additional30')},
              'adversarial_injection_probe': injection_probe(records, plan, b, r_, j, evidence),
              'heldout_jobs_planned_but_not_run': sorted(set(plan['heldout']) - {r['jd_id'] for r in held}),
              'scope': 'One resume, one model, one reviewer, single run per job. dev_regression reuses the job the prompt was revised on and is not pooled with heldout.'}
    _save(root / 'results/evaluation_report.json', report)
    return report

def export(root, include_evidence):
    root = Path(root); report = evaluation_report(root); dest = root / 'EvidenceMatch_Results_v23.zip'
    with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted((root / 'results').glob('*.json')): z.write(p, 'results/' + p.name)
        z.write(root / 'eval_plan.json', 'eval_plan.json')
        if include_evidence: z.write(root / 'private/confirmed_evidence.json', 'private/confirmed_evidence.json')
    return dest, report

# ---------- browser runner import ----------
def import_browser_run(root, export_path):
    """Rebuild run records and audit files from the browser page's export, using the same validation code as the Python runner."""
    from evidencematch import GPT4O_INFO, apply_response, new_record, save_record
    root = Path(root); evidence = load_evidence(root); data = _load(export_path, None)
    if not data or data.get('format') != 'evidencematch-browser-run-1': raise ValueError('不是 EvidenceMatch 浏览器导出文件。')
    if data['evidence_hash'] != digest(evidence) or data['prompt_version'] != PROMPT_VERSION:
        raise ValueError('导出文件与当前简历证据或提示词版本不一致，拒绝导入。')
    jobs = all_jobs(root); plan = _load(root / 'eval_plan.json', {})
    def label(jd): return 'dev_regression' if jd in plan.get('dev_regression', []) else 'adversarial' if jd in plan.get('adversarial', []) else 'heldout'
    run_of = {}
    for attempt in data.get('failed_attempts', []):
        rec = new_record(jobs[attempt['jd_id']], evidence, GPT4O_INFO, label(attempt['jd_id']), runner='browser')
        rec.update(started_at_utc=attempt.get('started_at_utc'), latency_seconds=attempt.get('latency_seconds'), error=attempt.get('error'))
        save_record(rec, root / 'results')
    for run in data['runs']:
        job = jobs[run['jd_id']]; rec = new_record(job, evidence, GPT4O_INFO, label(run['jd_id']), runner='browser')
        # 'latency_seconds' in the first page version stopped the clock at the response headers, so it is kept under its true name only.
        rec.update(started_at_utc=run.get('started_at_utc'), latency_seconds=run.get('latency_total_seconds'), time_to_response_headers_seconds=run.get('latency_seconds'))
        try: apply_response(rec, run['response'], job, evidence, GPT4O_INFO)
        except (ValueError, KeyError, TypeError, IndexError) as e: rec['error'] = type(e).__name__ + ': ' + str(e)[:200]
        save_record(rec, root / 'results'); run_of[run['jd_id']] = rec
    note = 'user judged alone in the browser page'
    _save(root / 'results/requirement_audit.json', [{'run_id': run_of[a['jd_id']]['run_id'], **a, 'human_label_entered_before_model_label_shown': not a.get('model_label_visible', False), 'reviewer': 'user'}
                                                    for a in data['requirement_audit'] if a['jd_id'] in run_of])
    _save(root / 'results/human_audit.json', [{'run_id': run_of[a['jd_id']]['run_id'], **a, 'reviewer': 'user', 'review_process': note,
                                               'accepted': a['verdict'] == 'supported' and run_of[a['jd_id']]['status'] == 'ready_for_human_review'}
                                              for a in data['bullet_audit'] if a['jd_id'] in run_of])
    _save(root / 'results/job_audit.json', [{'run_id': run_of[a['jd_id']]['run_id'], **a} for a in data['job_audit'] if a['jd_id'] in run_of])
    return evaluation_report(root)
