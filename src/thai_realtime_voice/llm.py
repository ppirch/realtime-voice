import json
import httpx

class StreamingLLM:
    def __init__(self, base_url, api_key, model, system_prompt):
        self.url = base_url.rstrip('/') + '/chat/completions'
        self.api_key, self.model, self.system_prompt = api_key, model, system_prompt
    def stream(self, messages):
        headers = {'Content-Type':'application/json'}
        if self.api_key: headers['Authorization'] = f'Bearer {self.api_key}'
        payload = {'model':self.model, 'stream':True, 'messages':[{'role':'system','content':self.system_prompt}, *messages]}
        with httpx.stream('POST', self.url, headers=headers, json=payload, timeout=httpx.Timeout(connect=10, read=None, write=10, pool=10)) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line or not line.startswith('data: ') or line == 'data: [DONE]': continue
                data = json.loads(line[6:])
                token = data.get('choices',[{}])[0].get('delta',{}).get('content')
                if token: yield token
