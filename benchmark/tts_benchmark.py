import argparse
import time

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--text', required=True)
    p.add_argument('--model', default='facebook/mms-tts-tha')
    a = p.parse_args()
    from realtime_voice.tts_mms import MMSThaiTTS, TARGET_SR
    t = time.perf_counter(); tts = MMSThaiTTS(model_id=a.model); load_s = time.perf_counter() - t
    t = time.perf_counter(); wav = tts.synthesize(a.text); dt = time.perf_counter() - t
    print({'chars': len(a.text), 'model': a.model, 'load_seconds': round(load_s, 2),
           'wall_seconds': round(dt, 2), 'audio_seconds': round(len(wav) / TARGET_SR, 2),
           'rtf': round(dt / max(len(wav) / TARGET_SR, 1e-6), 2), 'status': 'ok'})
if __name__ == '__main__': main()
