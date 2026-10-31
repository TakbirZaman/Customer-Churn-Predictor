import hashlib
import json
import re
import sqlite3
import time
import uuid
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

MAX_ROWS=200_000
MAX_BYTES=25*1024*1024


def confined(root, name):
    root=Path(root).resolve()
    path=(root / name).resolve()
    if not path.is_relative_to(root) or path==root:
        raise ValueError('Path must stay within this session directory.')
    return path


def safe_upload(root, filename, data):
    if '/' in filename or '\\' in filename or filename.startswith('.'):
        raise ValueError('Upload a plain filename without directories.')
    if Path(filename).suffix.lower() not in ('.csv','.xlsx','.sqlite','.db'):
        raise ValueError('Supported files: CSV, XLSX, SQLite (.db/.sqlite).')
    if len(data)>MAX_BYTES:
        raise ValueError('File exceeds the 25 MB limit.')
    # Content address prevents accidental overwrite of previous analysis inputs.
    name=hashlib.sha256(data).hexdigest()[:10]+'_'+filename
    confined(root,name).write_bytes(data)
    return name


class Toolbox:
    def __init__(self, workspace, store=None, allow_web=False, allow_python=False):
        self.root=Path(workspace)
        self.data=self.root/'data'
        self.out=self.root/'outputs'
        self.data.mkdir(parents=True,exist_ok=True)
        self.out.mkdir(parents=True,exist_ok=True)
        self.store=store
        self.allow_web=allow_web
        self.allow_python=allow_python

    def frame(self, file, sheet=0):
        path=confined(self.data,file)
        if path.stat().st_size>MAX_BYTES:
            raise ValueError('File exceeds 25 MB.')
        if path.suffix.lower()=='.csv':
            df=pd.read_csv(path,nrows=MAX_ROWS+1)
        elif path.suffix.lower()=='.xlsx':
            # Reject decompression bombs before opening XML.
            import zipfile
            with zipfile.ZipFile(path) as z:
                if sum(i.file_size for i in z.infolist())>150*1024*1024:
                    raise ValueError('Expanded workbook exceeds 150 MB.')
            df=pd.read_excel(path,sheet_name=sheet,nrows=MAX_ROWS+1)
        else:
            raise ValueError('Use CSV/XLSX for data analysis; query_sql for databases.')
        if len(df)>MAX_ROWS or len(df.columns)>150:
            raise ValueError('Dataset exceeds 200,000 rows or 150 columns. Split it first.')
        return df

    def list_files(self):
        return [{'file':p.name,'bytes':p.stat().st_size} for p in sorted(self.data.iterdir())
                if p.is_file() and not p.is_symlink()]

    def inspect_data(self, file, sheet=0):
        df=self.frame(file,sheet)
        result={'file':file,'rows':len(df),'columns':len(df.columns),'dtypes':df.dtypes.astype(str).to_dict(),
                'missing':df.isna().sum().to_dict(),'duplicate_rows':int(df.duplicated().sum()),
                'numeric_summary':df.describe().to_dict() if len(df.select_dtypes('number').columns) else {}}
        if Path(file).suffix.lower()=='.xlsx':
            with pd.ExcelFile(confined(self.data,file)) as book:
                result['sheets']=book.sheet_names
        return result

    def aggregate(self, file, value, group_by=None, operation='sum', date_column=None, frequency='M', sheet=0):
        if operation not in ('sum','mean','median','min','max','count','nunique'):
            raise ValueError('Unsupported aggregation.')
        df=self.frame(file,sheet)
        if value not in df:
            raise ValueError(f'Column {value!r} not found. Available: {list(df.columns)}')
        keys=list(group_by or [])
        invalid_dates=0
        if date_column:
            if frequency not in ('D','W','M','Q','Y'): raise ValueError('Use D/W/M/Q/Y frequency.')
            parsed=pd.to_datetime(df[date_column],errors='coerce')
            invalid_dates=int(parsed.isna().sum())
            df=df.assign(_period=parsed.dt.to_period(frequency).astype('string'))
            keys.append('_period')
        for key in keys:
            if key not in df: raise ValueError(f'Column {key!r} not found.')
        if operation not in ('count','nunique') and not pd.api.types.is_numeric_dtype(df[value]):
            raise ValueError('Numeric operation requires a numeric column. Clean data explicitly using Python.')
        if not keys:
            val=getattr(df[value],operation)()
            result=pd.DataFrame({'metric':[operation+'('+value+')'],'value':[val]})
        else:
            result=df.groupby(keys,dropna=False)[value].agg(operation).reset_index(name='value')
        name='aggregate_'+uuid.uuid4().hex[:8]+'.csv'
        result.to_csv(self.out/name,index=False)
        independent=None
        if operation=='sum':
            import math
            independent=math.fsum(float(x) for x in df[value].dropna())
        return {'rows':json.loads(result.head(50).to_json(orient='records')),'total_groups':len(result),
                'source_rows':len(df),'missing_values':int(df[value].isna().sum()),
                'invalid_dates':invalid_dates,'independent_sum_check':independent,'artifact':name,
                'method':operation, 'note':'Missing group labels retained; count excludes null values.'}

    def chart(self, file, x, y, kind='bar', title='Analysis', sheet=0):
        if kind not in ('bar','line','scatter'): raise ValueError('Use bar, line, or scatter.')
        # Charts accept original data or generated aggregate CSVs.
        if file.startswith('outputs/'):
            df=pd.read_csv(confined(self.out,file[8:]))
        else: df=self.frame(file,sheet)
        if x not in df or y not in df: raise ValueError('Chart columns do not exist.')
        if len(df)>500: raise ValueError('Aggregate first: charts are limited to 500 rows.')
        if not pd.api.types.is_numeric_dtype(df[y]): raise ValueError('Y column must be numeric.')
        fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
        if kind=='scatter': ax.scatter(df[x],df[y],color='#0d9488')
        elif kind=='line': ax.plot(df[x].astype(str),df[y],marker='o',color='#0d9488')
        else: ax.bar(df[x].astype(str),df[y],color='#0d9488')
        ax.set(title=title,xlabel=x,ylabel=y)
        ax.tick_params(axis='x',labelrotation=35)
        ax.spines[['top','right']].set_visible(False)
        name='chart_'+uuid.uuid4().hex[:8]+'.png'
        fig.savefig(self.out/name,dpi=140)
        plt.close(fig)
        return {'artifact':name,'plotted_rows':len(df)}

    def query_sql(self, file, query):
        path=confined(self.data,file)
        if path.suffix.lower() not in ('.sqlite','.db'): raise ValueError('Expected a SQLite database.')
        if not path.exists(): raise ValueError('Database not found.')
        if len(query)>10000: raise ValueError('Query too long.')
        with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as c:
            c.execute('PRAGMA query_only=ON')
            c.execute('PRAGMA trusted_schema=OFF')
            allowed={sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION,sqlite3.SQLITE_RECURSIVE}
            def authorize(action,a,b,db,source):
                if action==sqlite3.SQLITE_FUNCTION and str(b).lower() in ('load_extension','writefile','readfile'):
                    return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY
            c.set_authorizer(authorize)
            deadline=time.monotonic()+3
            c.set_progress_handler(lambda: int(time.monotonic()>deadline),1000)
            cur=c.execute(query)
            rows=cur.fetchmany(101)
            return {'columns':[d[0] for d in cur.description or []], 'rows':rows[:100],
                    'truncated':len(rows)>100,'note':'At most 100 rows returned; query timed out after 3 seconds if expensive.'}

    def web_search(self, query):
        if not self.allow_web: raise ValueError('Web research is disabled in settings.')
        key='search:'+query.strip().lower()
        if self.store:
            hit=self.store.cached(key)
            if hit is not None: return hit
        from ddgs import DDGS
        hits=list(DDGS(timeout=15).text(query,max_results=5))
        result={'query':query,'retrieved_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                'sources':[{'title':r.get('title',''),'url':r.get('href',''),'snippet':r.get('body','')[:900]} for r in hits],
                'note':'Search snippets only; verify primary pages before treating claims as established.'}
        if self.store: self.store.cache(key,result)
        return result

    def write_report(self, title, markdown):
        if len(markdown)>80000: raise ValueError('Report too long.')
        name=re.sub(r'[^a-zA-Z0-9_-]+','-',title).strip('-')[:60] or 'report'
        name+='-'+uuid.uuid4().hex[:8]+'.md'
        (self.out/name).write_text('# '+title+'\n\n'+markdown,encoding='utf-8')
        return {'artifact':name}

    def run_python(self, code):
        if not self.allow_python: raise ValueError('Python runner disabled. Enable Docker execution in settings.')
        from .runner import execute
        return execute(self.data,self.out,code)

    def analyze_retention(self, file, currency="unspecified", sheet=0):
        from .churn import run
        return run(self, file, currency, sheet)

    def dispatch(self,name,args):
        if name not in {s['function']['name'] for s in self.schemas()}:
            raise ValueError('Unknown or disabled tool.')
        return getattr(self,name)(**args)

    def schemas(self):
        def s(name,desc,props,required=()):
            return {'type':'function','function':{'name':name,'description':desc,'parameters':{
                'type':'object','properties':{k:({'type':v} if isinstance(v,str) else v) for k,v in props.items()},
                'required':list(required),'additionalProperties':False}}}
        file={'file':'string','sheet':{'type':'integer','description':'Excel sheet index, default 0'}}
        schemas=[s('analyze_retention','Score telecom customers via local churn API and save risk chart, customer priority CSV, segment CSV, individual model sensitivity explanations and business report. Synthetic model; not causal. Currency must be supplied by user or unspecified.',{**file,'currency':'string'},['file']),
            s('list_files','List available uploaded input filenames.',{}),
            s('inspect_data','Check rows, types, missing values, duplicates, numeric summary before analysis.',file,['file']),
            s('aggregate','Compute numeric metrics. Returns CSV artifact and independent total sum check.',
                {**file,'value':'string','group_by':{'type':'array','items':{'type':'string'}},'operation':{'type':'string','enum':['sum','mean','median','min','max','count','nunique']},'date_column':'string','frequency':'string'},['file','value']),
            s('chart','Chart input or outputs/aggregate_NAME.csv. Aggregate first for large datasets.',
                {**file,'x':'string','y':'string','kind':'string','title':'string'},['file','x','y']),
            s('query_sql','Read-only SQLite query. Discover tables using SELECT name FROM sqlite_master.',
                {'file':'string','query':'string'},['file','query']),
            s('write_report','Save Markdown report: Summary, Data & Method, Findings, Recommendations, Risks, Sources.',
                {'title':'string','markdown':'string'},['title','markdown'])]
        if self.allow_web: schemas.append(s('web_search','Research market facts; returns dated search snippets with URLs.',{'query':'string'},['query']))
        if self.allow_python: schemas.append(s('run_python','Execute Python in disposable offline Docker. Read files from /data, write CSV/PNG/MD/JSON to /outputs. Variables do NOT persist; include all code and imports each call.',{'code':'string'},['code']))
        return schemas
