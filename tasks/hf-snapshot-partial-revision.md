# HF の repo に新しい revision が出ると、load 後に「not activated」で 503 になるのを直す

## 起きたこと（2026-11-16、サーバー機）

- `mlx-community/Qwen3.8-27B-4bit` に新しい revision（`b935172`）が出ていた。chat の load が `snapshot_download` で新しい revision を落とし、
  `refs/main` がそちらを向いた。落としたのは load に要るファイルだけで、`README.md` が無かった
- 次の request から `setup_manager.ensure_ready` が「not activated」と判定して 503 を返した（同じ process で 1 回目の request は通っている）
- HF の cache は本番と共有なので、本番でも同じことが起きうる。`uv run kiapi activate --repo <repo>` で埋めれば戻る（blob は共有なので数秒）

## やること

1. load 側と `_hf_status` の判定をそろえる。案: load は `local_files_only` で activate 済みの snapshot を使う（勝手に新しい revision へ動かない）、
   または判定を load に要るファイルだけで行う
2. 新しい revision への追従は `kiapi activate` で明示的に行う、と README か ARCHITECTURE に書く

## ついでに直す

- `scripts/capabilities/verify_web.py` の binary URL の case が `https://www-media.blazeworks.jp/content/icon/miineko.png` を使っているが、
  この名前の DNS が無くなった（502）。残っている公開の画像の URL に替える
