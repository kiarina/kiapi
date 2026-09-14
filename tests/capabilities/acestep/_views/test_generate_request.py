from kiapi.capabilities.acestep import GenerateRequest


def test_generate_request_defaults_and_params() -> None:
    req = GenerateRequest(prompt="ambient piano", lyrics="[Instrumental]", duration=30)

    assert req.model == "xl-base"
    assert req.mode == "sync"
    assert req.gen_params() == {
        "prompt": "ambient piano",
        "lyrics": "[Instrumental]",
        "duration": 30,
        "lang": "ja",
        "seed": -1,
        "inference_steps": None,
        "guidance_scale": None,
        "shift": None,
    }
