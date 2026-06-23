"""Build the tiny :class:`ChatParams` used to prime MLX kernels at startup.

A 1-token, deterministic request for the given model variant — each model's
``warmup(payload)`` feeds it to ``run`` so the first real request isn't slowed by
kernel compilation.
"""

from .._views.chat_params import ChatParams


def warmup_params(model: str) -> ChatParams:
    return ChatParams(
        model=model,
        messages=[{"role": "user", "content": "hi"}],
        tools=None,
        tool_choice=None,
        parallel_tool_calls=True,
        max_tokens=1,
        temperature=0.0,
        top_p=1.0,
        seed=None,
        fps=1.0,
        use_audio_in_video=False,
        chat_template_kwargs=None,
        stream=False,
    )
