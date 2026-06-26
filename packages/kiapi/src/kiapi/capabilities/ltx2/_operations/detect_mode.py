"""Infer the LTX-2 generation mode from attached inputs."""


def detect_mode(
    *, has_image: bool, has_end_image: bool, has_audio: bool, generate_audio: bool
) -> str:
    is_i2v = has_image or has_end_image

    if has_audio:
        return "A2V+I2V" if is_i2v else "A2V"

    if is_i2v:
        if has_image and has_end_image:
            return "I2V(first+last)"
        if has_end_image:
            return "I2V(last)"
        return "I2V"

    return "T2V+Audio" if generate_audio else "T2V"
