import json
from pathlib import Path

from gateway.platforms import base


def _read_index(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_cache_audio_writes_indexed_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "AUDIO_CACHE_DIR", tmp_path / "audio_cache")
    monkeypatch.setattr(base, "VOICE_CACHE_DIR", base.AUDIO_CACHE_DIR / "inbound")
    monkeypatch.setattr(base, "VOICE_CACHE_INDEX_PATH", base.VOICE_CACHE_DIR / "index.json")
    monkeypatch.setenv("HERMES_VOICE_CACHE_MAX_FILES", "20")
    monkeypatch.setenv("HERMES_VOICE_CACHE_MAX_BYTES", str(200 * 1024 * 1024))

    path = base.cache_audio_from_bytes(
        b"voice-bytes",
        ext=".ogg",
        platform="telegram",
        chat_id="123",
        message_id="456",
        file_id="f1",
        file_unique_id="u1",
    )

    cached = Path(path)
    assert cached.exists()
    assert cached.parent == base.VOICE_CACHE_DIR

    index = _read_index(base.VOICE_CACHE_INDEX_PATH)
    assert index["version"] == 1
    assert len(index["entries"]) == 1
    entry = index["entries"][0]
    assert entry["path"] == str(cached)
    assert entry["platform"] == "telegram"
    assert entry["chat_id"] == "123"
    assert entry["message_id"] == "456"
    assert entry["file_id"] == "f1"
    assert entry["file_unique_id"] == "u1"


def test_cache_audio_prunes_oldest_by_file_count(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "AUDIO_CACHE_DIR", tmp_path / "audio_cache")
    monkeypatch.setattr(base, "VOICE_CACHE_DIR", base.AUDIO_CACHE_DIR / "inbound")
    monkeypatch.setattr(base, "VOICE_CACHE_INDEX_PATH", base.VOICE_CACHE_DIR / "index.json")
    monkeypatch.setenv("HERMES_VOICE_CACHE_MAX_FILES", "2")
    monkeypatch.setenv("HERMES_VOICE_CACHE_MAX_BYTES", str(10 * 1024 * 1024))

    p1 = Path(base.cache_audio_from_bytes(b"a", message_id="1", platform="telegram"))
    p2 = Path(base.cache_audio_from_bytes(b"b", message_id="2", platform="telegram"))
    p3 = Path(base.cache_audio_from_bytes(b"c", message_id="3", platform="telegram"))

    assert not p1.exists()
    assert p2.exists()
    assert p3.exists()

    index = _read_index(base.VOICE_CACHE_INDEX_PATH)
    ids = [e["message_id"] for e in index["entries"]]
    assert ids == ["2", "3"]


def test_find_cached_audio_by_message_id_returns_latest(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "AUDIO_CACHE_DIR", tmp_path / "audio_cache")
    monkeypatch.setattr(base, "VOICE_CACHE_DIR", base.AUDIO_CACHE_DIR / "inbound")
    monkeypatch.setattr(base, "VOICE_CACHE_INDEX_PATH", base.VOICE_CACHE_DIR / "index.json")

    p1 = base.cache_audio_from_bytes(b"first", message_id="42", platform="telegram", chat_id="1")
    p2 = base.cache_audio_from_bytes(b"second", message_id="42", platform="telegram", chat_id="1")

    found = base.find_cached_audio_by_message_id("42", platform="telegram", chat_id="1")
    assert found == p2
    assert Path(p1).exists()
    assert Path(p2).exists()
