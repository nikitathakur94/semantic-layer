import importlib.util
from pathlib import Path
import zipfile

import duckdb
import pytest
import requests

spec=importlib.util.spec_from_file_location('ingest',Path(__file__).resolve().parents[2]/'scripts/ingest.py')
ingest=importlib.util.module_from_spec(spec)
spec.loader.exec_module(ingest)


def test_manual_zip_cache_and_idempotent_rows(tmp_path,monkeypatch):
    monkeypatch.setattr(ingest,'ROOT',tmp_path)
    monkeypatch.setattr(ingest,'CACHE',tmp_path/'data/cache/2025q4_nport.zip')
    monkeypatch.setenv('LAB_DB_PATH',str(tmp_path/'data/lab.duckdb'))
    archive=tmp_path/'manual.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for name in ingest.TABLES:
            z.writestr(f'{name}.tsv','ACCESSION_NUMBER\tNULL_FIELD\n00001\t\n00002\t5\n')
        z.writestr('FUND_REPORTED_HOLDING.tsv','should not be extracted')
    first=ingest.ingest(archive)
    monkeypatch.setattr(ingest.requests,'get',lambda *a,**kw: pytest.fail('Cached run used network'))
    second=ingest.ingest()
    assert first['sha256']==second['sha256']
    assert first['row_counts']==second['row_counts']==dict.fromkeys(ingest.TABLES,2)
    assert {p.name for p in (tmp_path/'data/raw').iterdir()}=={f'{t}.tsv' for t in ingest.TABLES}
    with duckdb.connect(str(tmp_path/'data/lab.duckdb')) as con:
        assert con.execute('select count(*) from raw.SUBMISSION where NULL_FIELD is null').fetchone()[0]==1


def test_bounded_retries_and_actionable_fallback(tmp_path,monkeypatch):
    monkeypatch.setattr(ingest,'CACHE',tmp_path/'archive.zip')
    waits=[]
    calls=[]
    def fail(*args,**kwargs):
        calls.append(kwargs)
        raise requests.HTTPError('503 temporary unavailable')
    monkeypatch.setattr(ingest.requests,'get',fail)
    monkeypatch.setattr(ingest.time,'sleep',waits.append)
    with pytest.raises(RuntimeError,match='make refresh ZIP='):
        ingest.download('Lab test lab@real-domain.org')
    assert len(calls)==4 and waits==[2,4,8]
    assert calls[0]['headers']['User-Agent']=='Lab test lab@real-domain.org'


def test_requires_identifying_contact_and_complete_zip(tmp_path):
    with pytest.raises(ValueError,match='SEC_USER_AGENT'):
        ingest.download('anonymous')
    archive=tmp_path/'incomplete.zip'
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('SUBMISSION.tsv','x')
    with pytest.raises(ValueError,match='REGISTRANT'):
        ingest.validate_zip(archive)
