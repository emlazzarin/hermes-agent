"""
Tests for audio cache utilities in gateway/platforms/base.py.

Covers: get_audio_cache_dir, cache_audio_from_bytes, cleanup_audio_cache.
"""

import json
import os
import time
from pathlib import Path

import pytest

from gateway.platforms.base import (
    cache_audio_from_bytes,
    cleanup_audio_cache,
    find_cached_audio_by_message_id,
    get_audio_cache_dir,
    get_voice_cache_dir,
)

# ---------------------------------------------------------------------------
# Fixture: redirect AUDIO_CACHE_DIR to a temp directory for every test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _redirect_cache(tmp_path, monkeypatch):
    """Point the module-level AUDIO_CACHE_DIR to a fresh tmp_path."""
    monkeypatch.setattr(
        "gateway.platforms.base.AUDIO_CACHE_DIR", tmp_path / "audio_cache"
    )


# ---------------------------------------------------------------------------
# TestGetAudioCacheDir
# ---------------------------------------------------------------------------

class TestGetAudioCacheDir:
    def test_creates_directory(self):
        cache_dir = get_audio_cache_dir()
        assert cache_dir.exists()
        assert cache_dir.is_dir()


# ---------------------------------------------------------------------------
# TestCacheAudioFromBytes
# ---------------------------------------------------------------------------

class TestCacheAudioFromBytes:
    def test_basic_caching(self):
        data = b"fake-ogg-bytes"
        path = cache_audio_from_bytes(data)
        assert os.path.exists(path)
        assert Path(path).read_bytes() == data

    def test_default_extension(self):
        path = cache_audio_from_bytes(b"data")
        assert path.endswith(".ogg")

    def test_indexes_message_metadata(self):
        path = cache_audio_from_bytes(
            b"voice",
            message_id="42",
            platform="telegram",
            chat_id="7",
            file_id="file-id",
            file_unique_id="unique-id",
        )
        assert find_cached_audio_by_message_id(
            "42", platform="telegram", chat_id="7"
        ) == path
        index = json.loads((get_voice_cache_dir() / "index.json").read_text())
        assert index["entries"][-1]["file_unique_id"] == "unique-id"

    def test_evicts_oldest_entry_at_count_limit(self, monkeypatch):
        monkeypatch.setattr("gateway.platforms.base.VOICE_CACHE_MAX_FILES", 2)
        first = cache_audio_from_bytes(b"one", message_id="1")
        cache_audio_from_bytes(b"two", message_id="2")
        cache_audio_from_bytes(b"three", message_id="3")
        assert not Path(first).exists()
        assert find_cached_audio_by_message_id("1") is None
        assert find_cached_audio_by_message_id("3") is not None


# ---------------------------------------------------------------------------
# TestCleanupAudioCache
# ---------------------------------------------------------------------------

class TestCleanupAudioCache:
    def test_removes_old_files(self):
        cache_dir = get_audio_cache_dir()
        old_file = cache_dir / "old.ogg"
        old_file.write_text("old")
        # Set modification time to 48 hours ago
        old_mtime = time.time() - 48 * 3600
        os.utime(old_file, (old_mtime, old_mtime))

        removed = cleanup_audio_cache(max_age_hours=24)
        assert removed == 1
        assert not old_file.exists()

    def test_keeps_recent_files(self):
        cache_dir = get_audio_cache_dir()
        recent = cache_dir / "recent.ogg"
        recent.write_text("fresh")

        removed = cleanup_audio_cache(max_age_hours=24)
        assert removed == 0
        assert recent.exists()


# ---------------------------------------------------------------------------
# TestUnifiedMediaCacheCleanup — video + screenshot ride the same shared loop
# ---------------------------------------------------------------------------

class TestUnifiedMediaCacheCleanup:

    def test_cleanup_screenshot_cache_removes_old_files(self, tmp_path, monkeypatch):
        from gateway.platforms.base import (
            cleanup_screenshot_cache,
            get_screenshot_cache_dir,
        )

        monkeypatch.setattr(
            "gateway.platforms.base.SCREENSHOT_CACHE_DIR", tmp_path / "screenshots"
        )
        cache_dir = get_screenshot_cache_dir()
        old_file = cache_dir / "old.png"
        old_file.write_text("old")
        old_mtime = time.time() - 48 * 3600
        os.utime(old_file, (old_mtime, old_mtime))
        fresh = cache_dir / "fresh.png"
        fresh.write_text("fresh")

        removed = cleanup_screenshot_cache(max_age_hours=24)
        assert removed == 1
        assert not old_file.exists()
        assert fresh.exists()

