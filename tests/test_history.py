from realtime_voice.history import ConversationHistory


def test_short_history_passes_through_untouched():
    h = ConversationHistory(max_recent=4)
    h.add('user', 'สวัสดี')
    h.add('assistant', 'สวัสดีครับ')
    assert h.build() == [
        {'role': 'user', 'content': 'สวัสดี'},
        {'role': 'assistant', 'content': 'สวัสดีครับ'},
    ]
    assert h.summary == ''


def test_long_history_is_bounded_and_summarized_once():
    calls = []
    h = ConversationHistory(max_recent=4)
    for i in range(5):
        h.add('user', f'q{i}')
        h.add('assistant', f'a{i}')
    h.build(summarize=lambda old: calls.append(old) or f'sum({len(old)})')
    assert len(calls) == 1 and len(calls[0]) == 6  # first 6 msgs folded once
    h.wait()
    msgs = h.build(summarize=lambda old: calls.append(old) or 'again')
    assert len(msgs) == 5  # summary + last 4
    assert msgs[0]['role'] == 'system' and 'sum(6)' in msgs[0]['content']
    assert [m['content'] for m in msgs[1:]] == ['q3', 'a3', 'q4', 'a4']
    # rebuild without new old turns: no second summarization call
    h.build(summarize=lambda old: calls.append(old) or 'again')
    assert len(calls) == 1


def test_summary_grows_incrementally():
    seen = []
    h = ConversationHistory(max_recent=2)
    h.add('user', 'ผมชื่อต้น')
    h.add('assistant', 'ยินดีที่ได้รู้จัก')
    h.add('user', 'ชอบกินข้าวผัด')
    h.add('assistant', 'อร่อยดี')
    h.build(summarize=lambda old: seen.append([m['content'] for m in old]) or 's1')
    h.wait()
    h.add('user', 'พรุ่งนี้เจอกัน')
    h.add('assistant', 'ได้เลย')
    h.build(summarize=lambda old: seen.append([m['content'] for m in old]) or 's2')
    h.wait()
    msgs = h.build()
    assert seen == [['ผมชื่อต้น', 'ยินดีที่ได้รู้จัก'], ['ชอบกินข้าวผัด', 'อร่อยดี']]
    assert 's1' in msgs[0]['content'] and 's2' in msgs[0]['content']
    assert [m['content'] for m in msgs[1:]] == ['พรุ่งนี้เจอกัน', 'ได้เลย']


def test_transcript_keeps_everything_build_does_not():
    from realtime_voice.history import ConversationHistory
    h = ConversationHistory(max_recent=2)
    for i in range(5):
        h.add("user", f"q{i}")
    assert [m["content"] for m in h.transcript()] == [f"q{i}" for i in range(5)]
    # without a summarizer nothing is confirmed: payload keeps everything
    # rather than silently dropping context
    assert [m["content"] for m in h.build()] == [f"q{i}" for i in range(5)]
    h.build(summarize=lambda msgs: "s")
    h.wait()
    assert [m["content"] for m in h.build()[1:]] == ["q3", "q4"]


def _fill(h, n):
    for i in range(n):
        h.add("user", f"q{i}")


def test_build_does_not_block_on_slow_summarizer():
    import threading

    from realtime_voice.history import ConversationHistory
    release = threading.Event()
    calls = []

    def slow_summarize(msgs):
        calls.append([m["content"] for m in msgs])
        release.wait(timeout=10)
        return "old stuff"

    h = ConversationHistory(max_recent=2)
    _fill(h, 5)
    # summarizer stuck, but build() must return immediately with the
    # not-yet-summarized turns still in the payload (nothing lost)
    got = h.build(summarize=slow_summarize)
    assert [m["content"] for m in got] == [f"q{i}" for i in range(5)]
    release.set()
    h.wait()
    # next build: summary folded, payload back to bounded
    got = h.build(summarize=slow_summarize)
    assert got[0]["role"] == "system" and "old stuff" in got[0]["content"]
    assert [m["content"] for m in got[1:]] == ["q3", "q4"]
    assert len(calls) == 1  # each old turn summarized exactly once


def test_summarizer_exception_does_not_break_loop():
    from realtime_voice.history import ConversationHistory

    def boom(msgs):
        raise RuntimeError("llm down")

    h = ConversationHistory(max_recent=2)
    _fill(h, 4)
    got = h.build(summarize=boom)
    h.wait()
    assert [m["content"] for m in got] == ["q0", "q1", "q2", "q3"]
    # failed range retries on a later turn instead of poisoning history
    _fill(h, 1)
    h.build(summarize=lambda msgs: "recovered")
    h.wait()
    got = h.build()
    assert "recovered" in got[0]["content"]
