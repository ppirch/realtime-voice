from .config import Settings
from .audio import Microphone, Speaker
from .history import ConversationHistory
from .llm import StreamingLLM
from .stt import Qwen3ASRStreaming
from .tts_mms import MMSThaiTTS
from .text import sentence_chunks


def main():
    s = Settings.from_env()
    if not s.llm_model:
        raise SystemExit("Set LLM_MODEL in .env")

    llm = StreamingLLM(
        s.llm_base_url,
        s.llm_api_key,
        s.llm_model,
        s.system_prompt,
        protocol=s.llm_protocol,
    )
    asr = Qwen3ASRStreaming()
    tts = MMSThaiTTS()
    history = ConversationHistory(max_recent=8)

    def summarize_older(msgs):
        joined = '\n'.join(f"{m['role']}: {m['content']}" for m in msgs)
        prompt = (
            'สรุปบทสนทนาต่อไปนี้สั้นๆ ไม่เกิน 80 คำ เป็นภาษาไทย '
            'เน้นชื่อผู้ใช้ ความชอบ และเรื่องที่ค้างอยู่:\n' + joined
        )
        return ''.join(llm.stream([{'role': 'user', 'content': prompt}]))

    print("Thai Realtime Voice — Ctrl-C to quit")
    with Microphone(s.sample_rate, s.input_chunk_ms) as mic:
        speaker = Speaker(s.tts_sample_rate)
        while True:
            for event in asr.stream(mic.chunks(), sample_rate=s.sample_rate):
                if not getattr(event, "is_final", False) or not event.text.strip():
                    continue

                text = event.text.strip()
                print(f"You: {text}")
                history.add("user", text)

                answer = ""
                for chunk in sentence_chunks(llm.stream(history.build(summarize=summarize_older))):
                    print(chunk, end="", flush=True)
                    answer += chunk
                    speaker.play(tts.synthesize(chunk))

                print()
                history.add("assistant", answer)
