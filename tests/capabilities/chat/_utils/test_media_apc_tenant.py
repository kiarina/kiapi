from pathlib import Path

from kiapi.capabilities.chat._utils.media_apc_tenant import media_apc_tenant


def test_media_identity_uses_content_not_path(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    first.write_bytes(b"same image")
    second.write_bytes(first.read_bytes())
    key = media_apc_tenant("tenant", [str(first)], [], [])
    assert key == media_apc_tenant("tenant", [str(second)], [], [])
    first.write_bytes(b"changed image")
    assert key != media_apc_tenant("tenant", [str(first)], [], [])


def test_media_identity_separates_order_modality_and_tenant(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    first.write_bytes(b"a")
    second.write_bytes(b"b")
    a, b = str(first), str(second)
    key = media_apc_tenant("one", [a, b], [], [])
    assert key != media_apc_tenant("one", [b, a], [], [])
    assert key != media_apc_tenant("one", [], [a, b], [])
    assert key != media_apc_tenant("two", [a, b], [], [])


def test_video_options_invalidate_even_when_frames_are_unchanged(
    tmp_path: Path,
) -> None:
    video = tmp_path / "video"
    video.write_bytes(b"video")
    paths = [str(video)]
    key = media_apc_tenant("tenant", [], [], paths, fps=1)
    assert key != media_apc_tenant("tenant", [], [], paths, fps=2)
    assert key != media_apc_tenant("tenant", [], [], paths, use_audio_in_video=True)
    assert media_apc_tenant("tenant", [], [], []) == "tenant"
