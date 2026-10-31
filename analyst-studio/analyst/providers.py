"""Small OpenAI-compatible client with bounded retries and provider cooldowns."""
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass
class Provider:
    name: str
    url: str
    key: str
    model: str


def configured(local_only=False):
    specs = {
        'groq': ('https://api.groq.com/openai/v1','GROQ_API_KEY','openai/gpt-oss-120b'),
        'gemini': ('https://generativelanguage.googleapis.com/v1beta/openai','GEMINI_API_KEY',''),
        'openrouter': ('https://openrouter.ai/api/v1','OPENROUTER_API_KEY','openrouter/free'),
        'ollama': (os.getenv('OLLAMA_BASE_URL','http://localhost:11434/v1'),'',''),
    }
    result=[]
    for name in os.getenv('PROVIDER_ORDER','groq,gemini,openrouter,ollama').split(','):
        name=name.strip()
        if name not in specs or (local_only and name!='ollama'):
            continue
        url, keyvar, default=specs[name]
        key=os.getenv(keyvar,'') if keyvar else 'ollama'
        model=os.getenv(name.upper()+'_MODEL',default).strip()
        if not key or not model:
            continue
        if name=='openrouter' and not (model.endswith(':free') or model=='openrouter/free'):
            raise ValueError('OpenRouter must use openrouter/free or a :free model.')
        result.append(Provider(name,url,key,model))
    return result


class ProviderUnavailable(RuntimeError):
    pass


class Pool:
    def __init__(self, providers=None, transport=None, clock=time.time, sleep=time.sleep):
        self.providers=configured() if providers is None else providers
        self.transport=transport or self._http
        self.clock, self.sleep=clock,sleep
        self.cooldown={}
        self.last_usage={}
        self.notices=[]

    @staticmethod
    def _http(p, payload):
        req=urllib.request.Request(p.url.rstrip('/')+'/chat/completions',
            data=json.dumps(payload).encode(), headers={'Authorization': 'Bearer '+p.key,
            'Content-Type':'application/json'}, method='POST')
        with urllib.request.urlopen(req,timeout=60) as r:
            return json.load(r)

    def complete(self, messages, schemas):
        if not self.providers:
            raise ProviderUnavailable('No provider configured. Add a key/model to .env, or use the offline demo.')
        self.notices=[]
        for p in self.providers:
            if self.cooldown.get(p.name,0)>self.clock():
                continue
            for attempt in range(2):
                try:
                    payload={'model':p.model,'messages':messages,'max_tokens':1800}
                    if schemas:
                        payload.update(tools=schemas,tool_choice='auto')
                    response=self.transport(p,payload)
                    msg=response['choices'][0]['message']
                    self.last_usage={'provider':p.name, 'model':p.model, **response.get('usage',{})}
                    # Preserve provider-specific tool-call metadata, including Gemini signatures.
                    return {k:v for k,v in msg.items() if v is not None and k not in ('refusal','audio')}
                except urllib.error.HTTPError as e:
                    status=e.code
                    if status==429:
                        try: delay=max(1,float(e.headers.get('Retry-After','60')))
                        except (ValueError,AttributeError): delay=60
                        self.cooldown[p.name]=self.clock()+delay
                        self.notices.append(f'{p.name}: quota/rate limit; trying next configured provider.')
                        break
                    if status>=500 and attempt==0:
                        self.sleep(1)
                        continue
                    self.notices.append(f'{p.name}: HTTP {status}; check key, model and provider availability.')
                    self.cooldown[p.name]=self.clock()+60
                    break
                except (OSError, ValueError, KeyError, IndexError) as e:
                    self.notices.append(f'{p.name}: unavailable ({type(e).__name__}).')
                    self.cooldown[p.name]=self.clock()+30
                    break
        raise ProviderUnavailable('All configured providers are unavailable or cooling down. '
            'Your session is saved; retry after quota resets. '+' '.join(self.notices))
