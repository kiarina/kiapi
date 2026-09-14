"""Compatibility patch for Qwen3-Omni's image + video deepstack join.

When a prompt has both an image and a video, mlx-vlm 0.7.1's
``Thinker.get_input_embeddings`` joins the two deepstack feature sets with the
one-argument ``mx.where`` and ``mx.scatter``, which mlx does not provide, and it
``take``s rows from each modality's embeds using positions in the joint
sequence, so the video rows come from the wrong offsets. This rewrites only
that block, as upstream PR Blaizzy/mlx-vlm#2257 does: each modality's embeds are
assigned whole at its own positions. It changes nothing once the block no
longer matches, so drop it after mlx-vlm ships the fix.
"""

import inspect
import textwrap

_PATCH_FLAG = "_kiapi_image_video_join"

_OLD_BLOCK = """\
                visual_indices_flat = mx.where(visual_mask_flat)[0]
                image_mask_on_visual = mx.take(
                    image_mask_flat, visual_indices_flat, axis=0
                )
                video_mask_on_visual = mx.take(
                    video_mask_flat, visual_indices_flat, axis=0
                )
                image_indices = mx.where(image_mask_on_visual)[0]
                video_indices = mx.where(video_mask_on_visual)[0]

                visual_embeds_multiscale_joint = []
                for img_embed, vid_embed in zip(
                    visual_embeds_multiscale, video_embeds_multiscale
                ):
                    embed_joint = mx.zeros(
                        (len(visual_indices_flat), img_embed.shape[-1]),
                        dtype=img_embed.dtype,
                    )
                    if len(image_indices) > 0:
                        embed_joint = mx.scatter(
                            embed_joint,
                            image_indices,
                            mx.take(img_embed, image_indices, axis=0),
                            axis=0,
                        )
                    if len(video_indices) > 0:
                        embed_joint = mx.scatter(
                            embed_joint,
                            video_indices,
                            mx.take(vid_embed, video_indices, axis=0),
                            axis=0,
                        )
                    visual_embeds_multiscale_joint.append(embed_joint)
"""

_NEW_BLOCK = """\
                visual_indices = np.where(np.array(visual_mask_flat))[0]
                image_joint = mx.array(
                    np.where(np.array(image_mask_flat)[visual_indices])[0], mx.uint32
                )
                video_joint = mx.array(
                    np.where(np.array(video_mask_flat)[visual_indices])[0], mx.uint32
                )

                visual_embeds_multiscale_joint = []
                for img_embed, vid_embed in zip(
                    visual_embeds_multiscale, video_embeds_multiscale
                ):
                    embed_joint = mx.zeros(
                        (len(visual_indices), img_embed.shape[-1]),
                        dtype=img_embed.dtype,
                    )
                    if image_joint.size > 0:
                        embed_joint[image_joint] = img_embed
                    if video_joint.size > 0:
                        embed_joint[video_joint] = vid_embed
                    visual_embeds_multiscale_joint.append(embed_joint)
"""


def ensure_omni_image_video_join() -> bool:
    """Patch ``Thinker.get_input_embeddings`` once. Return whether it is patched."""
    try:
        from mlx_vlm.models.qwen3_omni_moe import thinker
    except Exception:
        return False

    cls = thinker.Thinker
    if getattr(cls, _PATCH_FLAG, False):
        return True

    source = inspect.getsource(cls.get_input_embeddings)
    if source.count(_OLD_BLOCK) != 1:
        return False

    patched = textwrap.dedent(source.replace(_OLD_BLOCK, _NEW_BLOCK))
    namespace: dict = {}
    exec(
        compile(patched, inspect.getsourcefile(cls) or "<thinker>", "exec"),
        vars(thinker),
        namespace,
    )
    cls.get_input_embeddings = namespace["get_input_embeddings"]  # type: ignore[method-assign]
    setattr(cls, _PATCH_FLAG, True)
    return True
