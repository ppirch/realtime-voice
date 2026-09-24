import argparse
import time

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--audio', required=True)
    p.add_argument('--model', default='Qwen/Qwen3-ASR-0.6B')
    p.add_argument('--language', default='Thai')
    a = p.parse_args()
    from mlx_qwen3_asr import load_audio, load_model, transcribe
    t = time.perf_counter(); model, _ = load_model(a.model); load_s = time.perf_counter() - t
    audio = load_audio(a.audio)
    t = time.perf_counter(); res = transcribe(audio, model=model, language=a.language); dt = time.perf_counter() - t
    print({'audio': a.audio, 'model': a.model, 'load_seconds': round(load_s, 2),
           'wall_seconds': round(dt, 2), 'rtf': round(dt / max(len(audio) / 16000, 1e-6), 2),
           'language': res.language, 'text': res.text, 'status': 'ok'})
if __name__ == '__main__': main()
