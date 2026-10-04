"""Recheck public job IDs and source hashes; never download private applicant data."""
import concurrent.futures,hashlib,json,urllib.request
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[0]
def verify(row):
    result={'jd_id':row['jd_id'],'source_url':row['source_url'],'checked_at_utc':datetime.now(timezone.utc).isoformat()}
    try:
        with urllib.request.urlopen(row['source_api'],timeout=25) as r:
            result['http_status']=r.status;job=json.load(r)
        result['job_id_matches']=str(job.get('id'))==row['source_job_id']
        result['nonempty_description']=bool(job.get('content','').strip())
        result['content_hash_matches']=hashlib.sha256(job.get('content','').encode()).hexdigest()==row['source_content_sha256']
        result['verified']=result['job_id_matches'] and result['nonempty_description']
    except Exception as e:result.update(verified=False,error=type(e).__name__)
    return result
if __name__=='__main__':
    jobs=json.loads((ROOT/'jd_additional_30.json').read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(verify,jobs))
    (ROOT/'source_verification.json').write_text(json.dumps(results,indent=2))
    print(json.dumps({'verified':sum(r['verified'] for r in results),'total':len(results),'hash_matches':sum(r.get('content_hash_matches',False) for r in results)}))
