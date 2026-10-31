import io
import json
from pathlib import Path
import sys

import pandas as pd
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'analyst-studio'))
sys.path.insert(0, str(ROOT/'backend'))
from app import app, model, preprocessor, reference, FEATURE_COLUMNS
from analyst.tools import Toolbox
from analyst import churn

client = TestClient(app)

@pytest.fixture
def sample():
    return pd.read_csv(ROOT/'sample_customers.csv',dtype={'customer_id':str})

def post(df, path='/retention-analysis?currency=BDT'):
    return client.post(path,files={'file':('customers.csv',df.to_csv(index=False).encode(),'text/csv')})

def test_full_batch_and_explanations(sample):
    response=post(sample)
    assert response.status_code==200,response.text
    r=response.json()
    assert r['summary']['total_customers']==len(sample)
    assert sum(s['customers'] for s in r['segments'] if s['dimension']=='contract_type')==len(sample)
    assert r['summary']['monthly_charge_exposure_proxy']==pytest.approx(sum(x['monthly_charges']*x['churn_probability'] for x in r['rows']),abs=.01)
    assert r['summary']['currency']=='BDT'
    for item in r['explanations']:
        row=sample.iloc[[item['row_number']-2]].copy()
        original=model.predict_proba(preprocessor.transform(row[FEATURE_COLUMNS]))[0,1]
        factor=item['top_factors'][0]
        row[factor['feature']]=reference[factor['feature']]
        replaced=model.predict_proba(preprocessor.transform(row[FEATURE_COLUMNS]))[0,1]
        assert factor['probability_difference']==pytest.approx(original-replaced,abs=1e-6)
    assert 'synthetic' in r['limitations']

@pytest.mark.parametrize('column,value',[('monthly_charges',-1),('monthly_charges',float('inf')),('tenure_months',1.5),('contract_type','Unknown'),('num_support_calls',None)])
def test_invalid_rows(sample,column,value):
    sample[column]=sample[column].astype(object)
    sample.loc[0,column]=value
    assert post(sample).status_code==422

def test_input_bounds(sample):
    assert post(sample.iloc[:0]).status_code==400
    assert post(sample.drop(columns=['monthly_charges'])).status_code==400
    assert post(pd.concat([sample.iloc[:1]]*5001)).status_code==400
    duplicate=sample.copy();duplicate['customer_id']='same'
    assert post(duplicate).status_code==400
    raw='a,a\n1,2\n'
    assert client.post('/predict-batch',files={'file':('x.csv',raw)}).status_code==400
    assert client.post('/predict-batch',files={'file':('x.csv',b'x'* (5*1024*1024+1))}).status_code==413
    assert post(sample,'/retention-analysis?currency=BADCODE').status_code==422
    assert post(sample,'/retention-analysis?explain_top=51').status_code==422

def test_backward_compatible_single_and_batch(sample):
    payload=sample.iloc[0][FEATURE_COLUMNS].to_dict()
    r=client.post('/predict',json=payload)
    assert r.status_code==200,r.text
    assert r.json()['explanation']['top_factors']
    batch=post(sample,'/predict-batch').json()
    assert batch['rows'][0]['churn_probability']==r.json()['churn_probability']

def test_connector_reports_and_privacy(sample,tmp_path,monkeypatch):
    sample['email']='private@example.com'
    box=Toolbox(tmp_path)
    sample.to_csv(box.data/'customers.csv',index=False)
    def request(path,data=None,headers=None):
        if data:
            assert b'private@example.com' not in data
            response=client.post(path,content=data,headers=headers)
        else: response=client.get(path)
        assert response.status_code==200,response.text
        return response.json()
    monkeypatch.setattr(churn,'request',request)
    r=box.dispatch('analyze_retention',{'file':'customers.csv','currency':'BDT'})
    assert 'private@example.com' not in json.dumps(r)
    assert 'rows' not in r and 'explanations' not in r
    for name in r['artifacts'].values(): assert (box.out/name).stat().st_size>0
    assert (box.out/r['artifacts']['chart']).read_bytes().startswith(b'\x89PNG')
    report=(box.out/r['artifacts']['report']).read_text()
    assert 'not expected lost revenue' in report and 'BDT' in report

@pytest.mark.parametrize('url',['https://example.com','http://169.254.169.254','http://localhost@evil.com','http://127.0.0.1/path'])
def test_local_only_url(monkeypatch,url):
    monkeypatch.setenv('CHURN_API_URL',url)
    with pytest.raises(ValueError): churn.base_url()

def test_csv_formula_escape(tmp_path):
    path=tmp_path/'safe.csv'
    churn.safe_csv(pd.DataFrame({'id':['=cmd()', '+1', 'normal']}),path)
    assert pd.read_csv(path).id.tolist()==["'=cmd()", "'+1",'normal']

def test_retention_agent_tool_loop(sample,tmp_path,monkeypatch):
    from analyst.agent import Agent
    from analyst.providers import Pool,Provider
    from analyst.storage import Store
    store=Store(tmp_path);sid=store.new();box=Toolbox(store.workspace(sid),store)
    sample.to_csv(box.data/'customers.csv',index=False)
    def request(path,data=None,headers=None):
        response=client.post(path,content=data,headers=headers) if data else client.get(path)
        response.raise_for_status()
        return response.json()
    monkeypatch.setattr(churn,'request',request)
    messages=iter([{'role':'assistant','tool_calls':[{'id':'churn1','type':'function','function':{'name':'analyze_retention','arguments':'{"file":"customers.csv"}'}}]},
                   {'role':'assistant','content':'Retention report saved. The model uses synthetic data.'}])
    def transport(provider,payload):
        return {'choices':[{'message':next(messages)}]}
    agent=Agent(store,sid,box,Pool([Provider('mock','url','key','model')],transport=transport))
    assert 'report saved' in agent.ask('Analyze customer retention')
    evidence=json.loads(agent.messages[-2]['content'])
    assert evidence['summary']['total_customers']==len(sample)
    assert (box.out/evidence['artifacts']['report']).is_file()


def test_retention_ui(sample,tmp_path,monkeypatch):
    from streamlit.testing.v1 import AppTest
    from analyst.storage import Store
    monkeypatch.setenv('ANALYST_HOME',str(tmp_path))
    monkeypatch.setenv('PROVIDER_ORDER','')
    def request(path,data=None,headers=None):
        response=client.post(path,content=data,headers=headers) if data else client.get(path)
        response.raise_for_status()
        return response.json()
    monkeypatch.setattr(churn,'request',request)
    ui=AppTest.from_file(str(ROOT/'analyst-studio/app.py')).run(timeout=30)
    sid=ui.session_state['sid']
    sample.to_csv(Store(tmp_path).workspace(sid)/'data'/'customers.csv',index=False)
    ui.run(timeout=30)
    next(b for b in ui.button if b.label=='Run retention analysis').click().run(timeout=30)
    assert not ui.exception
    assert ui.session_state['retention_'+sid]['summary']['total_customers']==len(sample)
    assert any(m.label=='High risk' for m in ui.metric)
    next(b for b in ui.button if 'New analysis' in b.label).click().run(timeout=30)
    assert not ui.exception
    assert not any(m.label=='High risk' for m in ui.metric)
