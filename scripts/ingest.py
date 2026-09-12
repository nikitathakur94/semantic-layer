"""Cache one SEC archive; load only three complete TSVs, atomically."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import time
import zipfile

import duckdb
from dotenv import load_dotenv
import requests

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PAGE = 'https://www.sec.gov/data-research/sec-markets-data/form-n-port-data-sets'
SOURCE_URL = 'https://www.sec.gov/files/dera/data/form-n-port-data-sets/2025q4_nport.zip'
TABLES = ('SUBMISSION', 'REGISTRANT', 'FUND_REPORTED_INFO')
CACHE = ROOT / 'data/cache/2025q4_nport.zip'


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def validate_zip(path):
    with zipfile.ZipFile(path) as archive:
        members = {Path(n).name.upper(): n for n in archive.namelist()}
        for table in TABLES:
            if f'{table}.TSV' not in members:
                raise ValueError(f'Archive missing {table}.tsv: {path}')
        return members


def download(user_agent):
    if not re.search(r'[^\s@]+@[^\s@]+\.[^\s@]+', user_agent) or 'example.com' in user_agent:
        raise ValueError('Set SEC_USER_AGENT to your name/organization and real contact email in .env')
    partial = CACHE.with_suffix('.part')
    for attempt in range(4):
        try:
            # Sequential requests, exponential backoff; well below SEC 10 req/s.
            with requests.get(SOURCE_URL, headers={'User-Agent': user_agent,
                              'Accept-Encoding': 'gzip, deflate'}, stream=True,
                              timeout=(30, 120)) as response:
                response.raise_for_status()
                with partial.open('wb') as output:
                    for chunk in response.iter_content(1024 * 1024):
                        output.write(chunk)
                validate_zip(partial)
                partial.replace(CACHE)
                return {'downloaded_at': now(), 'last_modified': response.headers.get('Last-Modified'),
                        'etag': response.headers.get('ETag'), 'method': 'https'}
        except (requests.RequestException, ValueError, zipfile.BadZipFile) as error:
            partial.unlink(missing_ok=True)
            print(f'SEC attempt {attempt + 1}/4: {error}', flush=True)
            if attempt < 3:
                time.sleep(2 ** (attempt + 1))
    raise RuntimeError('SEC download failed. Download 2025 Q4 in your browser from '
                       f'{SOURCE_PAGE}, then run make refresh ZIP=/absolute/path/2025q4_nport.zip')


def ingest(manual_zip=None):
    load_dotenv(ROOT / '.env')
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    metadata_path = CACHE.with_suffix('.json')
    if manual_zip:
        manual_zip = Path(manual_zip).expanduser().resolve()
        validate_zip(manual_zip)
        if manual_zip != CACHE:
            shutil.copyfile(manual_zip, CACHE)
        metadata = {'downloaded_at': None, 'imported_at': now(), 'method': 'manual_zip'}
    elif CACHE.exists():
        validate_zip(CACHE)
        metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {
            'downloaded_at': None, 'method': 'existing_cache'}
        print('Using cached archive', flush=True)
    else:
        metadata = download(os.environ.get('SEC_USER_AGENT', ''))
    metadata.update(source_page=SOURCE_PAGE, source_url=SOURCE_URL, quarter='2025Q4',
                    sha256=sha256(CACHE), bytes=CACHE.stat().st_size)
    metadata_path.write_text(json.dumps(metadata, indent=2))
    extracted = ROOT / 'data/raw'
    extracted.mkdir(exist_ok=True)
    counts = {}
    with zipfile.ZipFile(CACHE) as archive:
        members = validate_zip(CACHE)
        for table in TABLES:
            # Never extractall: holdings and all other tables remain in the ZIP.
            with archive.open(members[f'{table}.TSV']) as src, (extracted / f'{table}.tsv').open('wb') as dst:
                shutil.copyfileobj(src, dst)
    database = Path(os.environ.get('LAB_DB_PATH', str(ROOT / 'data/lab.duckdb')))
    database.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(database)) as con:
        con.execute('begin')
        con.execute('create schema if not exists raw')
        for table in TABLES:
            path = str(extracted / f'{table}.tsv')
            con.execute(f'create or replace table raw.{table} as select * from '
                        "read_csv(?, delim='\t', header=true, all_varchar=true, "
                        "nullstr='', quote='', strict_mode=true)", [path])
            counts[table] = con.execute(f'select count(*) from raw.{table}').fetchone()[0]
        con.execute('commit')
    metadata.update(ingested_at=now(), row_counts=counts,
                    extracted_tables=list(TABLES), database=str(database))
    (ROOT / 'data/ingestion_manifest.json').write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata, indent=2))
    return metadata


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', help='Manually downloaded official 2025 Q4 ZIP')
    ingest(parser.parse_args().zip)
