import argparse
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from analyst.storage import Store
from analyst.tools import Toolbox,safe_upload
from analyst.providers import Pool,configured
from analyst.agent import Agent
from analyst.demo import run


def main():
    root=Path(__file__).resolve().parent
    load_dotenv(root/'.env')
    p=argparse.ArgumentParser(description='Personal data + business analyst')
    p.add_argument('--demo',action='store_true',help='Run real demo calculations without a model')
    p.add_argument('--retention',action='store_true',help='Score --file using local churn API, without AI')
    p.add_argument('--currency',default='unspecified')
    p.add_argument('--ask',help='Ask the configured AI agent')
    p.add_argument('--file',type=Path,help='Copy an input into the current session')
    p.add_argument('--session',help='Resume a printed session ID')
    p.add_argument('--local-only',action='store_true')
    p.add_argument('--web',action='store_true')
    p.add_argument('--python',action='store_true',help='Enable isolated Docker execution')
    p.add_argument('--home',default=os.getenv('ANALYST_HOME',str(root/'.analyst')))
    args=p.parse_args()
    store=Store(args.home)
    sid=args.session or store.new()
    workspace=store.workspace(sid)
    if args.file:
        input_name=safe_upload(workspace/'data',args.file.name,args.file.read_bytes())
        print('Input:',input_name)
    if args.retention:
        if not args.file: p.error('--retention requires --file')
        result=Toolbox(workspace,store).analyze_retention(input_name,args.currency)
        store.event(sid,'retention',result)
        print(json.dumps(result,indent=2))
    elif args.demo:
        result=run(workspace)
        print(result['text'])
        store.save(sid,'Offline sample analysis',[{'role':'user','content':'Run demo'},
                   {'role':'assistant','content':result['text']}])
    elif args.ask:
        agent=Agent(store,sid,Toolbox(workspace,store,args.web,args.python),Pool(configured(args.local_only)))
        print(agent.ask(args.ask))
    else: p.print_help()
    print('\nSession:',sid,'\nOutputs:',workspace/'outputs')

if __name__=='__main__': main()
