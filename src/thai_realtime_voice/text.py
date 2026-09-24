import re
_BREAK = re.compile(r'([.!?。！？\n])')
def sentence_chunks(tokens, min_chars=12):
    buf=''
    for token in tokens:
        buf += token
        parts = _BREAK.split(buf)
        if len(parts)==1: continue
        buf=''
        for i in range(0, len(parts)-1, 2):
            chunk=(parts[i]+parts[i+1]).strip()
            if chunk: yield chunk
    if buf.strip(): yield buf.strip()
