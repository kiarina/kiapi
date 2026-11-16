# 推論経路の依存更新（transformers 5.23.0 ほか）を verify して main へ入れる

## 背景

2026-11-16 の依存保守の巡回で、推論経路に触れる lock の更新をブランチ `deps/inference-2026-11-16` に用意した。
推論経路の更新はサーバー機で full verify してから main へ入れる（サービスが止まるのでオーナーに確認する）。

- transformers 5.22.2 → 5.23.0（release note の breaking は `ep_router` の削除、Wav2Vec2ProcessorWithLM の非推奨、serve の attn。
  動画から取り出した音声を chat template に渡せるようになった）
- numpy 2.5.4 → 2.5.5、regex 2026.11.15、miniaudio 1.73、nagisa 0.3.2、filelock 4.2.10

## 確認済み

- `uv lock --upgrade` で消えるパッケージなし
- unit test 509 passed、import（transformers・numpy・mlx_audio・mlx_vlm・mflux・nagisa・miniaudio）
- branch の CI（`gh workflow run CI --ref deps/inference-2026-11-16`）

## やること

1. worktree でブランチを開き、`tests/assets` を link して `uv sync --inexact`
2. `mise run verify --kiapi`（全 family、full）。transformers は chat（Qwen の processor）・transcriptions・speech・画像の text encoder に効く。
   speech_call / speech_live は `--voice` を付けて手で回す（driver からは落ちる）
3. 通ったら `docs/playbooks/dependency-upgrades.md` の手順で main へ fast-forward し、サービスを再起動する

## 範囲外（別の判断）

- mlx-audio 0.6.1 → 0.6.5（Dependabot PR #35 は 0.6.4）。speech の patch を監査してからでないと上げられない
- huggingface-hub 2: mflux 0.24.0 が `huggingface-hub>=1.1.6,<2.0`
- mlx-vlm 0.7.12: `tasks/mlx-vlm-omni-patch-removal.md`
