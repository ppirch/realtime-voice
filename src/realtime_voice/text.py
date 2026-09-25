import re

_HARD = re.compile(r'([.!?。！？\n])')


def _soft_cut(buf, min_chars, target_chars, max_chars):
    """Return cut index for Thai text without hard delimiters, else None.

    Cut after the first space at/after ``min_chars`` once the buffer
    reaches ``target_chars``. Hard-cut at ``max_chars`` as a safety net
    so a chunk always arrives even without spaces.
    """
    if len(buf) < target_chars and len(buf) < max_chars:
        return None
    if len(buf) >= target_chars:
        sp = buf.find(' ', min_chars)
        if 0 < sp <= max_chars:
            return sp + 1
    if len(buf) >= max_chars:
        return max_chars
    return None


def sentence_chunks(tokens, min_chars=12, target_chars=30, max_chars=60):
    """Split streaming text into speakable chunks.

    Hard-split on sentence-final punctuation (any language), soft-split
    Thai phrase spaces every ~``target_chars`` chars so TTS can start
    before the full LLM response arrives. The remainder is never dropped.
    """
    buf = ''
    for token in tokens:
        buf += token
        parts = _HARD.split(buf)
        if len(parts) > 1:
            buf = parts[-1]
            for i in range(0, len(parts) - 1, 2):
                chunk = (parts[i] + parts[i + 1]).strip()
                if chunk:
                    yield chunk
        while True:
            cut = _soft_cut(buf, min_chars, target_chars, max_chars)
            if cut is None:
                break
            chunk, buf = buf[:cut].strip(), buf[cut:]
            if chunk:
                yield chunk
            elif not buf:
                break
    if buf.strip():
        yield buf.strip()
