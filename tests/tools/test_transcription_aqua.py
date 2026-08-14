"""Regression tests for the Aqua Voice Avalon STT provider."""

from types import SimpleNamespace

from tools import transcription_tools as tt


def test_explicit_aqua_requires_key(monkeypatch):
    monkeypatch.setattr(tt, "_resolve_provider_key", lambda env, provider: "")
    assert tt._get_provider({"enabled": True, "provider": "aqua"}) == "none"

    monkeypatch.setattr(tt, "_resolve_provider_key", lambda env, provider: "key")
    assert tt._get_provider({"enabled": True, "provider": "aqua"}) == "aqua"


def test_aqua_transcription_posts_openai_compatible_request(tmp_path, monkeypatch):
    audio = tmp_path / "voice.mp3"
    audio.write_bytes(b"fake audio")
    captured = {}

    class Response:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"text": "hello from aqua"}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(tt, "_resolve_provider_key", lambda env, provider: "aqua-key")
    monkeypatch.setattr(
        tt,
        "_load_stt_config",
        lambda: {"language": "en", "aqua": {"base_url": "https://aqua.test/v1"}},
    )
    monkeypatch.setitem(__import__("sys").modules, "requests", SimpleNamespace(post=fake_post))

    result = tt._transcribe_aqua(str(audio), "avalon-v1.5")

    assert result == {
        "success": True,
        "transcript": "hello from aqua",
        "provider": "aqua",
    }
    assert captured["url"] == "https://aqua.test/v1/audio/transcriptions"
    assert captured["headers"]["Authorization"] == "Bearer aqua-key"
    assert captured["data"] == {"model": "avalon-v1.5", "language": "en"}


def test_dispatch_routes_aqua(monkeypatch):
    expected = {"success": True, "transcript": "ok", "provider": "aqua"}
    monkeypatch.setattr(tt, "_transcribe_aqua", lambda *args, **kwargs: expected)

    result = tt._dispatch_stt_provider(
        "/tmp/voice.mp3",
        "aqua",
        {"aqua": {"model": "avalon-v1.5"}},
    )

    assert result == expected
