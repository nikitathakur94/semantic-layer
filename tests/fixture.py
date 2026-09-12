"""Seven tiny filings designed to expose semantic mistakes; never demo data."""
import duckdb


def create_fixture(path):
    con = duckdb.connect(str(path))
    con.execute('create schema raw')
    con.execute('create table raw.SUBMISSION(accession_number varchar, filing_date varchar, '
                'report_date varchar, report_ending_period varchar, sub_type varchar)')
    con.execute('create table raw.REGISTRANT(accession_number varchar, cik varchar, registrant_name varchar)')
    columns = ['accession_number','series_id','series_lei','series_name','net_assets'] + [
        f'{kind}_flow_mon{m}' for m in (1,2,3) for kind in ('sales','redemption','reinvestment')]
    con.execute('create table raw.FUND_REPORTED_INFO('+','.join(f'{n} varchar' for n in columns)+')')
    filings = [
        # September original then amendment: amendment must win (net assets 120).
        ('01','A','2025-09-30','2025-10-10','NPORT-P','100',[10,2,1,20,4,2,30,6,3]),
        ('02','A','2025-09-30','2025-10-11','NPORT-P/A','120',[11,2,1,21,4,2,31,6,3]),
        # October overlaps August/September and introduces an unknown September sale.
        ('03','A','2025-10-31','2025-11-10','NPORT-P','150',[22,5,2,None,7,3,40,8,4]),
        ('04','B','2025-09-30','2025-10-10','NPORT-P','200',[100,90,0,100,90,0,100,90,0]),
        ('05','NULL','2025-09-30','2025-10-10','NPORT-P',None,[None,None,None]*3),
        ('06','ZERO','2025-09-30','2025-10-10','NPORT-P','0',[0,5,0]*3),
        ('07','NEG','2025-09-30','2025-10-10','NPORT-P','-5',[-10,2,0]*3),
    ]
    for accession,fund,report,filed,kind,assets,flows in filings:
        con.execute('insert into raw.SUBMISSION values (?,?,?,?,?)',[accession,filed,report,'2025-12-31',kind])
        con.execute('insert into raw.REGISTRANT values (?,?,?)',[accession,'001','Franklin Test Trust'])
        values=[accession,fund,None,f'{fund} Test Fund',assets]+[str(v) if v is not None else None for v in flows]
        con.execute('insert into raw.FUND_REPORTED_INFO values ('+','.join('?' for _ in values)+')',values)
    # Exact duplicated source rows must not multiply joins or metrics.
    for table in ('SUBMISSION','REGISTRANT','FUND_REPORTED_INFO'):
        con.execute(f"insert into raw.{table} select * from raw.{table} where accession_number='02'")
    con.close()
