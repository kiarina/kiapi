# HISTORY

完了した作業、実測値、過去の意思決定の記録です。
作業日を含めて、新しいものを上に追記します。

## 2026-09-15 — mlx-vlm を 0.7.1 へ更新し、Omni の動画クラッシュを patch H で修正

- 目的は Qwen3-Omni の deepstack 修正（上流 #1635）。0.6.3 は vision の deepstack 特徴量を
  decoder の手前で捨てていた。0.7.1 で画像の回答が改善した（例: 「ピンクのツインテールの
  キャラクター」→「ピンク色の猫と赤いリボンが特徴の、ピクセルアートスタイルのキャラクター」）
- patch E（streaming UTF-8）と G（`mx.repeat`）は上流修正済みで削除。B / C / F は継続
- mlx-vlm 0.7 は mlx-lm を依存に持たなくなった。mlx-embeddings の qwen3_vl model が mlx-lm を
  top-level で import するため、kiapi で `mlx-lm>=0.31.3` を直接宣言した
- 0.7.1 では Omni に動画を送ると server が `[METAL] ... GPU Address Fault Error` で SIGABRT した
  （上流 issue #2099 と同じ）。原因は chunked prefill: full-prompt の `visual_pos_masks` と
  `deepstack_visual_embeds` が各 chunk（既定 2048 token）と最後の 1 token にそのまま渡り、
  `_deepstack_process` が chunk より長い位置へ scatter して GPU バッファの外に書く。
  動画（3611 token）は落ちるか `!!!!…` を出し、画像（84 token）は 1 行はみ出すだけで表に出ない
- 修正は patch H（`_operations/ensure_omni_deepstack_window.py`）。cache offset から mask と
  embeds を chunk の窓へ切り出す。上流の Qwen3-VL language model が既に行っている方式と同じ。
  Qwen3.6 / 3.8（qwen3_5）は deepstack が config で無効なので対象外
- 切り分け: deepstack を無効にすると動画は正しく答える → 呼び出しごとの形を記録すると
  hidden 2048 / 1562 / 1 に対して mask は常に 3611 → 窓を切ると動画・画像・動画+音声・画像+動画の
  4 通りとも deepstack を適用したまま正しく答えた
- サーバー機で `mise run verify --kiapi --family chat` を full で実行し、66 ケースと stream 検査
  8 件が通過。embedding の fast verify も通過。`make test` 280 passed
- 同じ修正を上流へ PR [Blaizzy/mlx-vlm#2256](https://github.com/Blaizzy/mlx-vlm/pull/2256) として出し、
  issue #2099 に原因をコメントした。上流版は batch の行ごとの offset にも対応し、回帰テストを追加した
  （修正前の main で失敗、修正後に通過）。実機でも動画・画像・動画+音声・画像+動画の 4 通りを確認
- 続けて kiapi の patch B / C に当たる上流の不具合も PR にした: image + video の deepstack 結合
  [#2257](https://github.com/Blaizzy/mlx-vlm/pull/2257)、stereo 音声の resample [#2258](https://github.com/Blaizzy/mlx-vlm/pull/2258)。
  どちらも回帰テスト付きで、実機で確認した（歌詞の引用が「Shh, don't you shh」168.6 秒 → 正しい歌詞 1.2 秒）。
  patch A は 0.7.1 では不要と確認
- kiapi の patch C にも #2257 と同じ誤り（video の deepstack 行を範囲外から読む）があったので直した。
  `Thinker.get_input_embeddings` の該当ブロックだけを #2257 と同じ処理に差し替える形にし、旧 shim
  （`mx.where` / `mx.scatter` の追加）は削除。上流のブロックが変わると何もせず、unit test が失敗する。
  worktree で chat の full verify（66 ケース + stream 8 件）が通過
- 落とし穴: 検証は本番 checkout ではなく git worktree で行った（kiapi は editable install なので、
  本番 checkout に WIP を置くとサービス再起動時に未検証コードが載る）。worktree には git 管理外の
  `tests/assets/` が無いので、本体の `tests/assets` を symlink しないと verify が画像で止まる

## 2026-09-15 — chat に Qwen3.8-27B を追加し、画像入力の mlx 0.32 非互換を修正

- `qwen3.8-27b`（`mlx-community/Qwen3.8-27B-4bit`、16.1 GB）を追加。MLX 版の
  `model_type` は Qwen3.6 と同じ `qwen3_5` で、chat template も Hermes/XML の tool call と
  `enable_thinking` を持つため、既存の `qwen3_5` handler をそのまま使う
- `vlm` / `qwen3-vl` / `qwen3_5` の alias を 3.6 から 3.8 へ移した。3.6 は `qwen3.6` だけ残す
- verify 中に、chat の画像入力が **全モデル（omni / 3.6 / 3.8）で 500** になっていたことが判明。
  mlx-vlm 0.6.3 の `qwen3_vl` / `qwen3_omni_moe` vision が `mx.repeat` に配列の回数を渡し、
  mlx 0.32.2 がこれを拒否する。mlx 0.32.2 は 2026-08-27 の lock 更新（`990cca7`）で入った。
  以後の verify は fast（text の 1 ケースだけ）だったため検出できなかった
- 修正は patch G（`_operations/ensure_vision_repeat_compat.py`）。該当 2 module の `mx` だけを、
  スカラー配列の回数を `int` にする proxy へ差し替える。mlx-vlm 0.7.1 の上流修正と同等。
  seedvr2 の失敗（mflux、回数が複数要素の配列）は別件で、この patch では直らない
- サーバー機で `mise run verify --kiapi --family chat` を full で実行し、3.8 / 3.6 / omni の
  全 66 ケース（stream 有無、omni の audio / video を含む）と stream 検証が通過。
  `make`、`make test`（277 passed）も通過
- 落とし穴: モデルを追加したら `kiapi activate --repo ...` で重みを取得するまで 503
  （not activated）になる。verify は取得しない

## 2026-09-15 — モノレポ構成をやめて単一パッケージ構成へ移行

- v0.6.0 で kiapi-relay / kiapi-proxy を削除して以降、workspace には kiapi しか
  残っていなかったため、uv workspace（`packages/kiapi`）をやめてリポジトリ直下を
  kiapi パッケージにした。今後も kiapi 単体しか扱わない前提
- ソースは `src/kiapi/`、単体テストは `tests/`（test-assets の `tests/assets/` と同居）へ移動。
  パッケージの `pyproject.toml` とルートの workspace / lint 設定を 1 つに統合
- パッケージ側の README（API 一覧、Requirements、Local Storage、Security）をルート
  README へ統合し、PyPI の readme もルート README になった。CHANGELOG はルートだけにし、
  既存エントリの `**kiapi**:` 接頭辞は過去の記録としてそのまま残した
- ルートの `VERSION` を廃止し、`pyproject.toml` の `version` を唯一のバージョンにした。
  `release:build` はタグと `pyproject.toml` の version が一致しない場合に失敗する
- mise タスクから `package:*` と package 引数を削除。release workflow の publish は
  package matrix をやめて kiapi 1 つを直接公開する
- sdist は `only-include = ["src"]` にして、ルートの docs / scripts / public などを
  含めないようにした（中身は src と README / LICENSE / pyproject のみ）
- サーバー機で `make`、`mise run test`（276 passed）、`mise run build` を確認。
  **release workflow 自体は次回リリースまで未実行**
- サーバー機で `mise run verify --kiapi --fast` を実行し、13 family 中 12 が通過。
  seedvr2 は mflux 0.19.1 と mlx 0.32.2 の非互換で失敗（移行とは無関係、
  `tasks/seedvr2-mflux-repeat-error.md`）
- 落とし穴: サーバー機では launchd サービスがこの checkout の `.venv` から動いている。
  移行作業中の `uv sync` で稼働中プロセスの依存が入れ替わり、anyio の import 失敗で
  全リクエストが 500 になった。verify がサービスを停止・再起動したことで復旧

## 2026-09-05 — 依存・Actions・Dependabot 設定の定期保守

- open alert 0 件・CI success の状態から、lockfile を `uv lock --upgrade` で更新。
  torch 2.13→2.14、torchvision 0.28→0.29、huggingface-hub 1.29→1.30、
  tokenizers 0.23.1→0.23.2、anyio 4.14.2→4.15.0、ruff 0.16.5→0.16.6 ほか計 10 件。
  `mlx-vlm==0.6.3` は chat のパッチ前提の意図的 pin なので据え置き
- torch は kiapi 本体から直接 import せず、transformers の Qwen processor 用に
  入れているだけなので、unit test では上げても差が出ない。開発機（Apple Silicon）で
  torch / torchvision / torchaudio の実 import と MPS 利用可否、`torchaudio.functional.resample`、
  `torchvision.transforms.v2.Resize` の実行まで確認した。torchaudio は 2.11.0 のまま
  torch 2.14 と共存する。**実モデル推論での検証は未実施**
- GitHub Actions を現行 major へ更新（checkout v6/v4→v7、configure-pages v5→v6、
  upload-pages-artifact v3→v5、deploy-pages v4→v5、upload-artifact v4→v7、
  download-artifact v4→v8）。落とし穴として、upload-pages-artifact は v4 以降
  dotfile を既定で除外するため、`public/.nojekyll` が黙って落ちる。
  `include-hidden-files: true` を明示して回避し、deploy 後に公開 URL の
  `.nojekyll` が 200 で返ることを確認した
- `.github/dependabot.yml` が陳腐化していた。npm ecosystem の記述は v0.6.0 で
  削除した root の `package.json` を指しており、どの manifest にも一致しない
  設定が残っていた。`uv` と `github-actions` の 2 ecosystem に置き換え、
  pin の理由が同じ `mlx-vlm` を ignore に入れた。push 後、両 ecosystem の
  Dependabot run が success で PR 0 件（＝現時点で追従漏れなし）を確認
- `packages/kiapi/pyproject.toml` の mlx-vlm コメントが存在しない
  `docs/mlx-vlm.md` を指していたので、実体の
  `src/kiapi/capabilities/chat/README.md` へ修正
- CI / release workflow が pin する mise を 2026.5.0 → 2026.9.1 へ更新。
  開発機の mise が 2026.9.1 で、その環境で `mise run ci` が通ることを確認済み
- 検証は開発機で `mise run ci`（lint + mypy 571 files + 276 tests + config/pages
  再生成 + build）を通し、生成物に差分が出ないことを確認。push 後の CI も success

## 2026-09-01 — relay を廃止して Tailscale 直結へ一本化（v0.6.0）

- ユーザー判断で併用評価（開始 2026-09-01）を短縮し、relay 廃止を決定。
  スモーク確認は省略（直結は日常利用中、git で戻せるためリスク許容）
- `packages/kiapi-relay` / `packages/kiapi-proxy`、relay runner の組み込み、
  `kiapi run --relay`、`/health` の `relay` フィールド、`relay-gcp` extra、
  `scripts/relay/`、`docs/concepts/relay.md` を削除（154 ファイル、約 7,300 行削減）。
  release パイプラインは `packages/*/` を動的検出するため削除に自動追従した
- 破壊的変更として v0.6.0 をリリース（CI / Release PyPI とも成功）。
  PyPI の `kiapi-relay` / `kiapi-proxy` には deprecation の最終リリースを
  出さない判断（実利用者が本人のみ。既存リリースは残置、以後更新しない）
- サーバー機へデプロイ時の落とし穴 2 件:
  - 削除済みパッケージの `__pycache__` 残骸が workspace glob `packages/*` に
    マッチして `uv run` が失敗。残骸ディレクトリの削除で解消
  - `tailscale serve --https=8500` が Tailscale IP の 8500 を掴むため、
    kiapi の `host: 0.0.0.0` bind が再起動時に EADDRINUSE で失敗
    （初回は kiapi が先に bind していたため共存できていた）。
    `host: 127.0.0.1` へ変更して解消。serve は 127.0.0.1 へ proxy するので
    tailnet 経由のアクセスは変わらず、tailnet 外への露出もなくなった
- サーバー機の `~/.config/kiapi/settings.yaml` から relay / google セクションを
  除去（backup: `settings.yaml.pre-relay-removal`）。lock 外の mlx-video は保全
- 開発機の kiapi-proxy launchd service は、editable install の実体が
  削除済みで CLI が使えないため、`launchctl bootout` + plist 削除で手動
  uninstall。`~/.config/kiapi-proxy/` も削除
- GCP の後始末（ユーザー承認済み）: GCS bucket `kiarina-kiapi`（relay セッション
  残骸 約 105KB のみ）を削除、Firebase RTDB インスタンス `kiarina-kiapi`
  （asia-southeast1）を disable → 削除。ADC は relay 専用ではないため残置
- relay を復活させる場合は git 履歴（v0.5.3 以前）と、当時の GCP 構築手順
  （`packages/kiapi-relay/.mise/tasks/gcp/setup`、削除済み）を参照

## 2026-09-01 — relay watch ハングの修正と Tailscale 直結の開始

- 2026-08-31、サーバー機の kiapi で RTDB SSE watch が無言のネットワーク断
  （18:53〜20:13 の DNS 断）で永久ハングし、proxy → kiapi が不通になった。
  heartbeat は watch と独立に生き残るため liveness からは検知できず、
  RTDB の `nodes/{node_id}/requests` に通知が 10 件滞留していた。kiapi 再起動で復旧
- 原因は共有 httpx クライアントの `read=None`。`0447ebc` で watch ストリームに
  読み取りタイムアウト（`watch_read_timeout_s`、既定 90 秒）を追加して修正し、
  サーバー機へデプロイ
- 実測: `/health` は relay 経由 1.1〜1.7 秒、Tailscale serve 直結 33ms
- relay 経由は応答を全量バッファするため chat streaming が逐次配信にならないことを
  `RelayRunner._dispatch` で確認
- これらを受けて relay 廃止の検討を開始（`tasks/remove-relay.md`）。
  サーバー機で `tailscale serve --bg --https=8500 8500` を開始し、
  kiari / spirits-garden の日常利用を直結へ切り替えて併用評価中
