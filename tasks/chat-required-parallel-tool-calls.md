# tool_choice: required で並列の tool call が 1 件しか返らない件を調べる

## 背景

2026-10-07、kiarina-agi-text の chat model の共通テスト（`tests/chat_model/_helpers/test_invoke_chat.py::test_tool_infos_parallel`）を
`qwen3.8-flash-next-fast`（`chat_template_kwargs.enable_thinking: false`）で流したところ、29 件中これだけが落ちた。
kiarina-agi-text の provider を LangChain 経由（`lc_openai`）から OpenAI SDK 直（`openai`）へ替えた確認の中で見つかったが、
`lc_openai` でも同じく落ちるので、provider ではなく kiapi 側（モデルか tool_choice の実装）の挙動。

再現の条件（Chat Completions）:

- user: `Tell me the weather and the latest news.`
- tools: `get_weather` と `get_news`（どちらも引数は `reason: string` だけ）
- `tool_choice: "required"`、`parallel_tool_calls: true`
- 期待: 2 件の tool call（`get_weather` と `get_news`）。実際: `get_weather` の 1 件だけ（4 回試して 4 回とも）
- `lc_openai` で流したときは、引数に schema に無い `restarts: ""` が混ざることもあった

`required` は assistant のターンを prefill して tool call を強制している（`src/kiapi/capabilities/chat/_operations/apply_template.py`）。
prefill が 1 件目の tool call の書き出しに固定されていて、そこで閉じてしまうのではないかと疑っている（未確認）。

## やること

- 上の条件を curl で再現し、`tool_choice: "auto"` と比べる（auto なら 2 件出るか）
- `enable_thinking: true` の `qwen3.8-flash-next`、ほかの chat model でも出るか見る
- 原因がモデルなのか、`required` の prefill・tool call の parse（`apply_parallel_tool_call_policy` を含む）なのかを切り分ける
- kiapi で直せるなら直し、回帰テストを足す。モデルの限界なら chat の README の `parallel_tool_calls` の節に書く

## 申し送り

- Codex を kiapi につなぐ用途（`/v1/responses`、2026-10-08）は `tool_choice: "auto"`・`parallel_tool_calls: true` で送ってくるので、この件には当たらない

## 完了条件

- 原因が分かり、直したか、モデルの挙動として README に書いた
- 直した場合は、kiarina-agi-text の `test_tool_infos_parallel` が `qwen3.8-flash-next-fast` で通る
  （`KIARINA_AGI_TEXT_TEST_CHAT_MODEL=qwen3.8-flash-next-fast` で `tests/chat_model/_helpers/` を流す。`local` の設定が要る）
