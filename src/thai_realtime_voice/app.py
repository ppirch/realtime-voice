from .config import Settings
from .audio import Microphone, Speaker
from .llm import StreamingLLM
from .stt import Qwen3ASRStreaming
from .tts import FastThaiG2PKokoro
from .text import sentence_chunks

def main():
    s=Settings.from_env()
    if not s.llm_model: raise SystemExit('Set LLM_MODEL in .env')
    llm=StreamingLLM(s.llm_base_url,s.llm_api_key,s.llm_model,s.system_prompt)
    asr=Qwen3ASRStreaming()
    tts=FastThaiG2PKokoro()
    history=[]
    print('Thai Realtime Voice — Ctrl-C to quit')
    with Microphone(s.sample_rate,s.input_chunk_ms) as mic:
        speaker=Speaker(s.tts_sample_rate)
        while True:
            for event in asr.stream(mic.chunks(), sample_rate=s.sample_rate):
                if not getattr(event,'is_final',False) or not event.text.strip(): continue
                text=event.text.strip(); print(f'You: {text}')
                history.append({'role':'user','content':text})
                answer=''
                for chunk in sentence_chunks(llm.stream(history)):
                    print(chunk, end='', flush=True); answer += chunk
                    speaker.play(tts.synthesize(chunk))
                print(); history.append({'role':'assistant','content':answer})
