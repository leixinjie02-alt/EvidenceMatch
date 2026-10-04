"""Fix the evaluation jobs BEFORE any v2.3 model call. Re-running reproduces the same plan (seeded)."""
import json, random
from pathlib import Path
ROOT = Path(__file__).resolve().parents[0]
SEED = 6201
jobs = json.loads((ROOT / 'jd_corpus_48.json').read_text())
rng = random.Random(SEED)
DEV = ['JD19']  # the only job seen while the prompt was revised
def pick(pool, k):
    return sorted(rng.sample(sorted(j['jd_id'] for j in pool if j['jd_id'] not in DEV), k))
new = [j for j in jobs if j['cohort'] == 'additional30']
strata = {
    'original18_chinese_text': (pick([j for j in jobs if j['cohort'] == 'original18'], 4)),
    'new_intern': pick([j for j in new if j['seniority'] == 'intern'], 1),
    'new_graduate_or_junior': pick([j for j in new if j['seniority'] in {'graduate', 'junior', 'early-career'} and j['role_family'] not in {'Robotics/CV'}], 1),
    'new_experienced': pick([j for j in new if j['seniority'] == 'experienced' and 'Robotics' not in j['role_family']], 2),
    'new_senior_or_above': pick([j for j in new if j['seniority'] in {'senior', 'lead', 'principal', 'senior/staff'} and j['role_family'] != 'Computer vision'], 1),
    'new_deliberate_mismatch_robotics_cv': pick([j for j in new if j['role_family'] in {'Robotics/CV', 'Robotics', 'Computer vision'}], 1),
}
plan = {'seed': SEED, 'dev_regression': DEV, 'adversarial': ['ADV01'], 'heldout_strata': strata,
        'heldout': sorted(x for v in strata.values() for x in v),
        'note': 'Stratified seeded sample fixed before any v2.3 call. dev_regression is reported separately and never pooled with heldout. adversarial is a single injection probe written by the author, also reported separately.'}
(ROOT / 'eval_plan.json').write_text(json.dumps(plan, indent=2))
print(json.dumps(plan, indent=2))
