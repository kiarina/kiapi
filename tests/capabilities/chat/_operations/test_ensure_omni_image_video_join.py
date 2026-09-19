import pytest

from kiapi.capabilities.chat._operations.ensure_omni_image_video_join import (
    ensure_omni_image_video_join,
)

mx = pytest.importorskip("mlx.core")
config = pytest.importorskip("mlx_vlm.models.qwen3_omni_moe.config")
omni = pytest.importorskip("mlx_vlm.models.qwen3_omni_moe.qwen3_omni_moe")

IMAGE_TOKEN, VIDEO_TOKEN, VISION_START, VISION_END = 60, 61, 63, 59


def _text_config(model_type):  # type: ignore
    return config.TextConfig(
        model_type=model_type,
        num_hidden_layers=2,
        hidden_size=16,
        intermediate_size=32,
        num_attention_heads=2,
        num_key_value_heads=2,
        head_dim=8,
        num_experts=0,
        num_experts_per_tok=1,
        decoder_sparse_step=1,
        mlp_only_layers=[],
        moe_intermediate_size=32,
        rms_norm_eps=1e-5,
        vocab_size=64,
        rope_theta=10000,
        max_position_embeddings=64,
    )


def _tiny_thinker():  # type: ignore
    thinker = config.ThinkerConfig(
        text_config=_text_config("qwen3_omni_moe_text_encoder"),
        vision_config=config.VisionConfig(
            depth=2,
            hidden_size=16,
            intermediate_size=32,
            out_hidden_size=16,
            num_heads=2,
            image_size=8,
            patch_size=2,
            spatial_patch_size=2,
            spatial_merge_size=2,
            in_channels=3,
            in_chans=3,
            num_position_embeddings=16,
            deepstack_visual_indexes=[0, 1],
        ),
        audio_config=config.AudioConfig(
            d_model=16,
            encoder_layers=0,
            encoder_attention_heads=2,
            encoder_ffn_dim=32,
            num_hidden_layers=0,
            num_mel_bins=8,
            output_dim=16,
            downsample_hidden_size=8,
        ),
        image_token_id=IMAGE_TOKEN,
        video_token_id=VIDEO_TOKEN,
        audio_token_id=62,
        vision_start_token_id=VISION_START,
        vision_end_token_id=VISION_END,
    )
    talker = config.TalkerConfig(
        text_config=_text_config("qwen3_omni_moe_talker_text"),
        code_predictor_config=config.CodePredictorConfig(
            num_hidden_layers=1,
            hidden_size=16,
            intermediate_size=32,
            num_attention_heads=2,
            num_key_value_heads=2,
            head_dim=8,
            vocab_size=32,
            num_code_groups=2,
        ),
        accept_hidden_layer=0,
        thinker_hidden_size=16,
    )
    code2wav = config.Code2WavConfig(
        hidden_size=16,
        intermediate_size=32,
        num_hidden_layers=1,
        num_attention_heads=2,
        num_key_value_heads=2,
        decoder_dim=16,
        codebook_dim=8,
        codebook_size=32,
        num_quantizers=2,
        num_semantic_quantizers=1,
        semantic_codebook_size=32,
        vector_quantization_hidden_dimension=8,
    )
    model = omni.Model(
        config.ModelConfig(
            thinker_config=thinker,
            talker_config=talker,
            code2wav_config=code2wav,
            enable_audio_output=False,
            im_start_token_id=10,
            im_end_token_id=11,
            system_token_id=12,
            user_token_id=13,
            assistant_token_id=14,
            tts_bos_token_id=15,
            tts_eos_token_id=16,
            tts_pad_token_id=17,
        )
    )
    return model.thinker


def test_image_and_video_deepstack_rows_land_at_their_own_positions():  # type: ignore
    with mx.stream(mx.cpu):
        ensure_omni_image_video_join()
        ensure_omni_image_video_join()

        thinker = _tiny_thinker()
        mx.random.seed(11)
        # One image and one video, each a 1x4x4 patch grid -> 4 visual tokens.
        pixel_values = mx.random.normal((16, 24))
        pixel_values_videos = mx.random.normal((16, 24))
        grid = mx.array([[1, 4, 4]])
        input_ids = mx.array(
            [
                [1, 2, VISION_START]
                + [IMAGE_TOKEN] * 4
                + [VISION_END, VISION_START]
                + [VIDEO_TOKEN] * 4
                + [VISION_END, 3]
            ],
            dtype=mx.int32,
        )

        joint = thinker.get_input_embeddings(
            input_ids,
            pixel_values=pixel_values,
            image_grid_thw=grid,
            pixel_values_videos=pixel_values_videos,
            video_grid_thw=grid,
        ).deepstack_visual_embeds
        _, image_only = thinker.vision_tower(pixel_values, grid)
        _, video_only = thinker.vision_tower(pixel_values_videos, grid)

        if getattr(joint, "ndim", None) == 4:
            # The pinned upstream fork expands deepstack residuals to all tokens.
            assert tuple(joint.shape) == (1, input_ids.shape[1], 2, 16)
            for layer in range(2):
                assert mx.allclose(
                    joint[0, 3:7, layer], image_only[layer], atol=1e-6
                ).item()
                assert mx.allclose(
                    joint[0, 9:13, layer], video_only[layer], atol=1e-6
                ).item()
        else:
            assert len(joint) == 2
            for rows, image_rows, video_rows in zip(
                joint, image_only, video_only, strict=True
            ):
                assert tuple(rows.shape) == (8, 16)
                assert mx.allclose(rows[:4], image_rows, atol=1e-6).item()
                assert mx.allclose(rows[4:], video_rows, atol=1e-6).item()
