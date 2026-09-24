from thai_realtime_voice.text import sentence_chunks
def test_sentence_chunks():
    assert list(sentence_chunks(iter(['สวัสดีครับ วันนี้ดีมากครับ! ขอบคุณ']))) == ['สวัสดีครับ วันนี้ดีมากครับ!', 'ขอบคุณ']
