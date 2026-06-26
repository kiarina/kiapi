from kiapi.capabilities.ltx2 import detect_mode


def test_detect_mode_returns_t2v_for_prompt_only() -> None:
    assert (
        detect_mode(
            has_image=False,
            has_end_image=False,
            has_audio=False,
            generate_audio=False,
        )
        == "T2V"
    )


def test_detect_mode_returns_t2v_audio_for_generated_audio() -> None:
    assert (
        detect_mode(
            has_image=False,
            has_end_image=False,
            has_audio=False,
            generate_audio=True,
        )
        == "T2V+Audio"
    )


def test_detect_mode_returns_i2v_variants() -> None:
    assert (
        detect_mode(
            has_image=True,
            has_end_image=False,
            has_audio=False,
            generate_audio=False,
        )
        == "I2V"
    )
    assert (
        detect_mode(
            has_image=False,
            has_end_image=True,
            has_audio=False,
            generate_audio=False,
        )
        == "I2V(last)"
    )
    assert (
        detect_mode(
            has_image=True,
            has_end_image=True,
            has_audio=False,
            generate_audio=False,
        )
        == "I2V(first+last)"
    )


def test_detect_mode_returns_audio_variants() -> None:
    assert (
        detect_mode(
            has_image=False,
            has_end_image=False,
            has_audio=True,
            generate_audio=False,
        )
        == "A2V"
    )
    assert (
        detect_mode(
            has_image=True,
            has_end_image=False,
            has_audio=True,
            generate_audio=False,
        )
        == "A2V+I2V"
    )
