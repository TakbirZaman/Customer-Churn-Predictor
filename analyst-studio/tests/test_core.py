import io
import json
import sqlite3
import urllib.error
from pathlib import Path
from unittest.mock import Mock
import pandas as pd
import pytest
from analyst.tools import Toolbox, safe_upload
from analyst.storage import Store
from analyst.providers import Pool, Provider, ProviderUnavailable, configured
from analyst.agent import Agent, compact
from analyst.demo import run

@pytest.fixture
def setup(tmp_path):
    store=Store(tmp_path)
    sid=store.new()
    box=Toolbox(store.workspace(sid),store)
    (box.data/'sales.csv').write_text('date,category,revenue\n2026-01-01,A,10\n2026-01-02,B,20\nbad,,5\n2026-02-01,A,\n')
    return store,sid,box


def test_quality_and_aggregate(setup):
    _,_,box=setup
    profile=box.inspect_data('sales.csv')
    assert profile['missing']['revenue']==1
    result=box.aggregate('sales.csv','revenue',group_by=['category'])
    assert result['independent_sum_check']==35
    assert sum(r['value'] for r in result['rows'])==35
    assert (box.out/result['artifact']).exists()
    monthly=box.aggregate('sales.csv','revenue',date_column='date')
    assert monthly['invalid_dates']==1
    assert sum(r['value'] for r in monthly['rows'])==35


def test_wrong_column(setup):
    with pytest.raises(ValueError,match='not found'): setup[2].aggregate('sales.csv','profit')


def test_traversal_and_upload(setup):
    box=setup[2]
    with pytest.raises(ValueError): box.frame('../../history.sqlite3')
    with pytest.raises(ValueError): safe_upload(box.data,'../bad.csv',b'hi')
    with pytest.raises(ValueError): safe_upload(box.data,'x\\bad.csv',b'hi')
    with pytest.raises(ValueError): safe_upload(box.data,'evil.py',b'hi')
    a=safe_upload(box.data,'safe.csv',b'x\n1')
    b=safe_upload(box.data,'safe.csv',b'x\n2')
    assert a!=b


def test_excel(setup):
    box=setup[2]
    pd.DataFrame({'a':[2,4]}).to_excel(box.data/'book.xlsx',index=False)
    assert box.inspect_data('book.xlsx')['rows']==2
    assert box.aggregate('book.xlsx','a')['rows'][0]['value']==6


def test_sql_security_and_cte(setup):
    box=setup[2]
    with sqlite3.connect(box.data/'db.sqlite') as c:
        c.executescript('CREATE TABLE t(x); INSERT INTO t VALUES(1),(2);')
    assert box.query_sql('db.sqlite','WITH a AS (SELECT SUM(x) AS total FROM t) SELECT * FROM a')['rows']==[(3,)]
    for query in ['DELETE FROM t','ATTACH DATABASE "/tmp/escape.db" AS other','PRAGMA table_info(t)',
                  'SELECT load_extension("evil")','SELECT 1; DELETE FROM t']:
        with pytest.raises(sqlite3.Error): box.query_sql('db.sqlite',query)
    assert box.query_sql('db.sqlite','SELECT COUNT(*) FROM t')['rows']==[(2,)]


def test_sql_row_limit(setup):
    box=setup[2]
    sqlite3.connect(box.data/'db.sqlite').close()
    result=box.query_sql('db.sqlite','WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<200) SELECT x FROM n')
    assert len(result['rows'])==100 and result['truncated']


def test_chart_and_report(setup):
    box=setup[2]
    result=box.aggregate('sales.csv','revenue',group_by=['category'])
    chart=box.chart('outputs/'+result['artifact'],'category','value')
    assert (box.out/chart['artifact']).read_bytes().startswith(b'\x89PNG')
    report=box.write_report('../../report','# Findings\n35 total')
    assert (box.out/report['artifact']).is_file()


def test_tools_opt_in(setup):
    box=setup[2]
    assert 'run_python' not in str(box.schemas())
    with pytest.raises(ValueError): box.dispatch('run_python',{'code':'print(1)'})
    with pytest.raises(ValueError): box.web_search('private data')


def test_provider_fallback_and_cooldown():
    calls=[]
    def transport(p,payload):
        calls.append(p.name)
        if p.name=='first': raise urllib.error.HTTPError('url',429,'limited',{'Retry-After':'120'},None)
        return {'choices':[{'message':{'role':'assistant','content':'ok'}}],'usage':{'total_tokens':10}}
    pool=Pool([Provider('first','url','secret','m'),Provider('second','url','secret','m')],transport=transport,clock=lambda:100)
    assert pool.complete([],[])['content']=='ok'
    assert calls==['first','second']
    pool.complete([],[])
    assert calls==['first','second','second']
    assert pool.last_usage['total_tokens']==10


def test_no_provider():
    with pytest.raises(ProviderUnavailable): Pool([]).complete([],[])


def test_paid_openrouter_rejected(monkeypatch):
    monkeypatch.setenv('PROVIDER_ORDER','openrouter')
    monkeypatch.setenv('OPENROUTER_API_KEY','test')
    monkeypatch.setenv('OPENROUTER_MODEL','paid/model')
    with pytest.raises(ValueError): configured()


def test_local_only(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','test')
    monkeypatch.setenv('OLLAMA_MODEL','local-model')
    assert [p.name for p in configured(True)]==['ollama']


def test_real_tool_agent_loop_and_resume(setup):
    store,sid,box=setup
    responses=iter([
        {'role':'assistant','tool_calls':[{'id':'call1','type':'function','function':{'name':'aggregate','arguments':json.dumps({'file':'sales.csv','value':'revenue'})}}]},
        {'role':'assistant','content':'Revenue total is 35.'}])
    pool=Pool([Provider('mock','url','key','m')],transport=lambda p,q:{'choices':[{'message':next(responses)}]})
    agent=Agent(store,sid,box,pool)
    assert agent.ask('Sum revenue')=='Revenue total is 35.'
    restored=Agent(store,sid,box,pool)
    assert restored.messages[-1]['content']=='Revenue total is 35.'
    assert json.loads(restored.messages[-2]['content'])['rows'][0]['value']==35
    assert store.events(sid)[1]['kind']=='tool'


def test_malformed_arguments_recover(setup):
    store,sid,box=setup
    messages=iter([
        {'role':'assistant','tool_calls':[{'id':'x','type':'function','function':{'name':'aggregate','arguments':'{broken'}}]},
        {'role':'assistant','content':'Arguments corrected next time.'}])
    pool=Pool([Provider('mock','url','key','m')],transport=lambda p,q:{'choices':[{'message':next(messages)}]})
    agent=Agent(store,sid,box,pool)
    agent.ask('test')
    assert 'error' in json.loads(agent.messages[-2]['content'])


def test_compact_keeps_tool_pairs():
    msgs=[{'role':'system','content':'s'},{'role':'user','content':'old'*100},
          {'role':'assistant','content':'done'},{'role':'user','content':'now'},
          {'role':'assistant','tool_calls':[{'id':'t'}]},{'role':'tool','tool_call_id':'t','content':'evidence'}]
    kept=compact(msgs,150)
    assert kept[1]['content']=='now'
    assert kept[-2]['tool_calls'][0]['id']==kept[-1]['tool_call_id']


def test_interruption_recovery(setup):
    store,sid,box=setup
    store.save(sid,'interrupted',[{'role':'system','content':'test'},{'role':'user','content':'q'},
        {'role':'assistant','tool_calls':[{'id':'t','function':{'name':'write_report','arguments':'{}'}}]}])
    agent=Agent(store,sid,box,Pool([]))
    assert agent.messages[-1]['role']=='tool'
    assert 'Interrupted' in agent.messages[-1]['content']


def test_cache_and_isolation(setup):
    store,sid,box=setup
    store.cache('x',{'answer':1})
    assert store.cached('x')=={'answer':1}
    store.cache('y',{},ttl=-1)
    assert store.cached('y') is None
    other=Toolbox(store.workspace(store.new()))
    assert other.list_files()==[]


def test_demo(tmp_path):
    result=run(tmp_path)
    assert result['totals']['independent_sum_check']==63000
    assert [r['value'] for r in result['monthly']['rows']]==[16000,30000,17000]


def test_step_limit(setup):
    store,sid,box=setup
    def transport(p,q):
        return {'choices':[{'message':{'role':'assistant','tool_calls':[{'id':'t','type':'function','function':{'name':'list_files','arguments':'{}'}}]}}]}
    agent=Agent(store,sid,box,Pool([Provider('mock','url','key','m')],transport=transport))
    assert 'step limit' in agent.ask('Loop',max_steps=2)
    assert len([e for e in store.events(sid) if e['kind']=='usage'])==2
