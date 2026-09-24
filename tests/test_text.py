from thai_realtime_voice.text import sentence_chunks


def _no_loss(original, chunks):
    norm = lambda s: s.replace(' ', '')
    assert norm(''.join(chunks)) == norm(original), chunks


def test_sentence_chunks():
    assert list(sentence_chunks(iter(['สวัสดีครับ วันนี้ดีมากครับ! ขอบคุณ']))) == ['สวัสดีครับ วันนี้ดีมากครับ!', 'ขอบคุณ']


def test_thai_soft_split_without_punctuation():
    text = 'สวัสดีครับคุณต้น ยินดีที่ได้รู้จักครับ มีอะไรให้ผมช่วยไหมครับ'
    chunks = list(sentence_chunks(iter([text])))
    assert len(chunks) >= 2, chunks
    _no_loss(text, chunks)


def test_no_text_lost_when_streaming_char_by_char():
    text = 'คุณต้นลองข้าวผัดไข่ครับ ง่ายมาก มีข้าว ไข่ ซีอิ๊ว ผัดห้านาทีเสร็จ อิ่มอร่อยครับ'
    chunks = list(sentence_chunks(iter(list(text))))
    assert len(chunks) >= 2, chunks
    _no_loss(text, chunks)


def test_long_word_without_spaces_is_hard_cut():
    text = 'ก' * 200
    chunks = list(sentence_chunks(iter([text])))
    assert len(chunks) >= 2, chunks
    assert all(len(c) <= 60 for c in chunks), chunks
    _no_loss(text, chunks)
