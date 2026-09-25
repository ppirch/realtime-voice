from realtime_voice.app import run_mic_loop
from realtime_voice.stt_endpoint import Utterance


class FakeMic:
    def __init__(self):
        self.flushed = 0

    def chunks(self):
        return iter([])

    def flush(self):
        self.flushed += 1


class FakeBackend:
    def __init__(self, events):
        self.events = events

    def stream(self, chunks, sample_rate=16000):
        yield from self.events


def _args(live=False, max_turns=0):
    from realtime_voice.app import parse_args
    argv = []
    if live:
        argv.append("--live")
    if max_turns:
        argv += ["--max-turns", str(max_turns)]
    return parse_args(argv)


def test_loop_dispatches_finals_and_counts():
    turns = []
    mic = FakeMic()
    backend = FakeBackend([Utterance("one"), Utterance("two")])
    n = run_mic_loop(_args(), backend, mic, 16000, 800,
                     on_turn=lambda t, i: turns.append((t, i)), settle=False)
    assert n == 2
    assert turns == [("one", 1), ("two", 2)]
    assert mic.flushed == 0  # no speaker echo without settle


def test_loop_max_turns_breaks_early():
    turns = []
    backend = FakeBackend([Utterance("one"), Utterance("two"), Utterance("three")])
    n = run_mic_loop(_args(max_turns=2), backend, FakeMic(), 16000, 800,
                     on_turn=lambda t, i: turns.append(t), settle=False)
    assert n == 2 and turns == ["one", "two"]


def test_loop_settle_flushes_between_turns():
    mic = FakeMic()
    backend = FakeBackend([Utterance("one"), Utterance("two")])
    run_mic_loop(_args(), backend, mic, 16000, 800,
                 on_turn=lambda t, i: None, settle=True)
    assert mic.flushed == 2


def test_loop_routes_previews_when_live():
    seen = []
    backend = FakeBackend([Utterance("hel", is_final=False),
                           Utterance("hello", is_final=True)])
    run_mic_loop(_args(live=True), backend, FakeMic(), 16000, 800,
                 on_turn=lambda t, i: None, settle=False,
                 on_preview=seen.append)
    assert seen == ["hel"]
