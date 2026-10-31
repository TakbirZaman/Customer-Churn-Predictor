from pathlib import Path
import json
import os
import shutil
import streamlit as st
from dotenv import load_dotenv
from analyst.storage import Store
from analyst.tools import Toolbox, safe_upload
from analyst.providers import Pool, configured
from analyst.agent import Agent
from analyst.demo import run as demo

ROOT=Path(__file__).resolve().parent
load_dotenv(ROOT/'.env')
st.set_page_config(page_title='Analyst Studio',page_icon='◈',layout='wide')
st.markdown('''<style>
.block-container{max-width:1160px;padding-top:2rem}
[data-testid="stMetric"]{background:white;border:1px solid #dce5eb;border-radius:14px;padding:16px}
h1{letter-spacing:-1.4px} .stCaption{color:#64748b}
</style>''',unsafe_allow_html=True)
store=Store(os.getenv('ANALYST_HOME',str(ROOT/'.analyst')))
if 'sid' not in st.session_state: st.session_state.sid=store.new()

with st.sidebar:
    st.markdown('## ◈ Analyst Studio')
    st.caption('Your data. Clearer decisions.')
    if st.button('＋ New analysis',width='stretch'):
        st.session_state.sid=store.new()
        st.session_state.session_picker=st.session_state.sid
        st.session_state.pop('pool',None)
        st.rerun()
    sessions=store.sessions()
    ids=[s[0] for s in sessions]
    titles=dict(sessions)
    selected=st.selectbox('Saved analyses',ids,index=ids.index(st.session_state.sid),format_func=lambda x:titles[x],key='session_picker')
    if selected!=st.session_state.sid:
        st.session_state.sid=selected
        st.rerun()
    st.divider()
    local_only=st.toggle('Local models only',value=False,help='Use only Ollama. No cloud fallback.')
    web=st.toggle('Allow web research',value=False,help='Sends search queries to third-party search services.')
    python=st.toggle('Enable Docker Python',value=False,help='Requires Docker plus the supplied runner image.')
    if local_only and web: st.caption('Model is local; web searches still use the internet.')
    st.caption('Cloud mode sends your question, data summaries, tool outputs and recent chat to configured providers. Raw rows may appear in SQL/Python output.')
    st.markdown('[Provider setup](https://console.groq.com/keys) · See START_HERE.md for instructions')

sid=st.session_state.sid
workspace=store.workspace(sid)
box=Toolbox(workspace,store,allow_web=web,allow_python=python)
try: providers=configured(local_only)
except ValueError as e:
    st.error(str(e)); providers=[]
pool_key=tuple((p.name,p.url,p.model) for p in providers)
if st.session_state.get('pool_key')!=pool_key or 'pool' not in st.session_state:
    st.session_state.pool=Pool(providers)
    st.session_state.pool_key=pool_key
agent=Agent(store,sid,box,st.session_state.pool)

st.caption('PERSONAL ANALYTICS WORKSPACE')
st.title('From questions to evidence.')
st.write('Explore your data, research a business idea, and turn the findings into a report.')
left,right=st.columns([3,2])
with left:
    st.caption('CONNECTED MODELS')
    st.write(' → '.join(p.name+' / '+p.model for p in providers) or 'No model connected · offline demo available')
with right:
    st.caption('ANALYSIS TOOLS')
    st.write('Data quality · Aggregates · Charts · Read-only SQL')
st.divider()
chat_tab,data_tab,retention_tab,files_tab,activity_tab=st.tabs(['Ask & analyze','Data explorer','Customer retention','Reports & charts','Activity'])

with data_tab:
    upload=st.file_uploader('Add your data',type=['csv','xlsx','sqlite','db'],help='Up to 25 MB; 200,000 rows for tabular analysis.')
    if upload:
        try:
            name=safe_upload(box.data,upload.name,upload.getvalue())
            st.success('Available as: '+name)
        except Exception as e: st.error(str(e))
    files=box.list_files()
    if files:
        selected_file=st.selectbox('Explore file',[f['file'] for f in files])
        if Path(selected_file).suffix.lower() in ('.csv','.xlsx'):
            try:
                sheet=0
                if selected_file.endswith('.xlsx'):
                    import pandas as pd
                    with pd.ExcelFile(box.data/selected_file) as book:
                        names=book.sheet_names
                    sheet=names.index(st.selectbox('Worksheet',names))
                profile=box.inspect_data(selected_file,sheet)
                cols=st.columns(3)
                cols[0].metric('Rows',f"{profile['rows']:,}")
                cols[1].metric('Columns',profile['columns'])
                cols[2].metric('Duplicate rows',profile['duplicate_rows'])
                st.dataframe(box.frame(selected_file,sheet).head(100),width='stretch')
                with st.expander('Data quality details'): st.json(profile)
            except Exception as e: st.error(str(e))
        else:
            st.info('Ask the agent to list tables or run a read-only SQL query against this database.')
    else: st.info('Upload a file or run the sample analysis to start.')

with chat_tab:
    if st.button('Try a complete sample analysis — no key needed',width='stretch'):
        result=demo(workspace)
        agent.messages.extend([{'role':'user','content':'Run the bundled synthetic sales demonstration.'},
                               {'role':'assistant','content':result['text']}])
        agent.save()
        store.event(sid,'demo',{'total':result['totals']['independent_sum_check']})
        st.rerun()
    if not providers:
        st.info('The sample runs real calculations immediately. For free-form AI chat, add a provider key to .env or configure a local Ollama model, then restart.')
    for message in agent.messages:
        if message['role'] in ('user','assistant') and message.get('content'):
            with st.chat_message(message['role']): st.markdown(message['content'])
    question=st.chat_input('What would you like to understand?',disabled=not bool(providers))
    if question:
        with st.chat_message('user'): st.write(question)
        with st.status('Working through the evidence…',expanded=True) as status:
            def progress(kind,payload):
                if kind=='tool': st.write('✓ '+payload['name'])
                elif kind in ('notice','provider_error','tool_error'): st.write(payload)
            try:
                answer=agent.ask(question,on_event=progress)
                status.update(label='Analysis saved',state='complete',expanded=False)
            except Exception as e:
                answer='Analysis stopped: '+str(e)
                status.update(label='Analysis stopped',state='error')
        with st.chat_message('assistant'): st.markdown(answer)
    st.caption('Try: “Inspect my file and report revenue by month, with a chart.” Or enable web research and ask about a business idea.')

with retention_tab:
    st.subheader('Customer retention analysis')
    st.caption('Score customers, compare segments, and download a prioritized report. No AI key required.')
    st.warning('The included model uses synthetic telecom data. Validate it on real, held-out business data before using scores for decisions.')
    if st.button('Check churn connection'):
        try:
            from analyst.churn import status
            info=status()
            st.success('Connected · model '+str(info['model_version']))
        except Exception as e: st.error(str(e))
    sample=ROOT/'data'/'sample_customers.csv'
    if sample.exists():
        st.download_button('Download customer CSV template',sample.read_bytes(),file_name='sample_customers.csv')
    churn_upload=st.file_uploader('Customer CSV',type=['csv'],key='retention_upload')
    if churn_upload:
        try: safe_upload(box.data,churn_upload.name,churn_upload.getvalue())
        except Exception as e: st.error(str(e))
    candidates=[f['file'] for f in box.list_files() if f['file'].endswith('.csv')]
    if candidates:
        customer_file=st.selectbox('Customer file',candidates,key='retention_file')
        currency=st.text_input('Currency code (leave unspecified if unknown)',value='unspecified',key='retention_currency')
        if st.button('Run retention analysis',type='primary'):
            try:
                with st.spinner('Scoring customers and preparing evidence…'):
                    result=box.analyze_retention(customer_file,currency.strip())
                store.event(sid,'retention',result)
                st.session_state['retention_'+sid]=result
            except Exception as e: st.error(str(e))
    else: st.info('Upload customer data here or in Data explorer.')
    if 'retention_'+sid not in st.session_state:
        saved=[e['payload'] for e in store.events(sid) if e['kind']=='retention']
        if saved: st.session_state['retention_'+sid]=saved[-1]
    retention=st.session_state.get('retention_'+sid)
    if retention:
        summary=retention['summary']
        cols=st.columns(3)
        cols[0].metric('Customers',summary['total_customers'])
        cols[1].metric('High risk',summary['high_risk_count'])
        cols[2].metric('Average model score',f"{summary['avg_churn_probability']:.1%}")
        st.dataframe(retention['segments'],width='stretch')
        st.image(str(box.out/retention['artifacts']['chart']))
        st.success('Report, priority list and explanations saved in Reports & charts.')
        for kind,name in retention['artifacts'].items():
            st.download_button('Download '+kind,(box.out/name).read_bytes(),file_name=name,key='retention_'+name)

with files_tab:
    artifacts=[p for p in sorted(box.out.iterdir(),key=lambda p:p.stat().st_mtime,reverse=True)
               if p.is_file() and not p.is_symlink()]
    if not artifacts: st.info('Charts, aggregate CSVs, and Markdown reports will appear here.')
    for path in artifacts:
        with st.expander(path.name,expanded=path.suffix=='.png'):
            if path.suffix=='.png': st.image(str(path))
            elif path.suffix=='.md': st.markdown(path.read_text(encoding='utf-8'))
            st.download_button('Download '+path.suffix.lstrip('.').upper(),path.read_bytes(),file_name=path.name,key=path.name)
    transcript='\n\n'.join('## '+m['role'].title()+'\n\n'+m.get('content','') for m in agent.messages
                           if m['role'] in ('user','assistant') and m.get('content'))
    st.download_button('Download conversation',transcript,file_name='analysis-conversation.md')

with activity_tab:
    events=store.events(sid)
    calls=[e for e in events if e['kind']=='usage']
    col1,col2=st.columns(2)
    col1.metric('Model calls',len(calls))
    col2.metric('Reported tokens',sum(e['payload'].get('total_tokens',0) or 0 for e in calls))
    st.caption('Tool arguments and results are retained locally for reproducibility. No API keys are logged.')
    st.json(events[-40:])
    st.download_button('Download full audit log',json.dumps(events,indent=2),file_name='analysis-audit.json')
