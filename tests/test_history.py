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
    msgs = h.build(summarize=lambda old: calls.append(old) or f'sum({len(old)})')
    assert len(calls) == 1 and len(calls[0]) == 6  # first 6 msgs folded once
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
    h.add('user', 'พรุ่งนี้เจอกัน')
    h.add('assistant', 'ได้เลย')
    msgs = h.build(summarize=lambda old: seen.append([m['content'] for m in old]) or 's2')
    assert seen == [['ผมชื่อต้น', 'ยินดีที่ได้รู้จัก'], ['ชอบกินข้าวผัด', 'อร่อยดี']]
    assert 's1' in msgs[0]['content'] and 's2' in msgs[0]['content']
    assert [m['content'] for m in msgs[1:]] == ['พรุ่งนี้เจอกัน', 'ได้เลย']
