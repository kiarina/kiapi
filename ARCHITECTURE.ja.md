# kiapi アーキテクチャ

[English](ARCHITECTURE.md) | **日本語**

## リポジトリ構成

- ファイル構成は Crystal Architecture を採用する
  - [kiarina/crystal-architecture](https://github.com/kiarina/crystal-architecture)
- 設定管理は、Pydantic Settings Manager を採用する
  - [kiarina/pydantic-settings-manager](https://github.com/kiarina/pydantic-settings-manager)

このリポジトリは、独立してバージョン管理される 3 パッケージを持つ uv workspace である。

```sh
packages/
  kiapi/        # src/kiapi/        MLX 推論 API サーバー（Apple Silicon）
  kiapi-relay/  # src/kiapi_relay/  relay トランスポート（プラットフォーム非依存、gcp extra）
  kiapi-proxy/  # src/kiapi_proxy/  relay 経由で kiapi に中継する HTTP Proxy
```

`kiapi` と `kiapi-proxy` はともに `kiapi-relay` に依存する。`kiapi-proxy` は `kiapi`
に依存しないため、MLX なしでインストールでき、どこでも動作する。

`kiapi` パッケージ（`packages/kiapi/src/kiapi`）の構成は次の通り。

```sh
kiapi/
  core/                # 能力非依存の土台
    app/               # アプリ全体のコンテキスト、起動配線、ユーザーディレクトリ解決
    model/             # モデルレジストリ（全ファミリーの ModelSpec カタログ・resolve）
    setup/             # セットアップ管理（HF snapshot / Docker image / local path の status・activate・deactivate）
    memory/            # メモリ予算マネージャ（常駐管理・退避・TTL 掃引）
    worker/            # シングルフライト worker（専用 1 スレッド + キュー）
    job/               # 統一ジョブモデル + インメモリジョブストア
    file/              # 統一ファイルストア（file_id 採番・メタ・ディスク保存）
    workdir/           # 実行中の一時作業ディレクトリ管理
    net/               # ネットワークガード（ユーザー指定 URL の SSRF 検証）
    logging/           # ロギング設定

  capabilities/        # ファミリーごとに 1 パッケージ（dir == family）
    chat/              # OpenAI 互換 chat completions（マルチモーダル / tool / stream）
    embedding/         # マルチモーダル embedding
    zimage/            # 画像生成（Z-Image、LoRA 学習）
    flux2/             # 画像生成・編集（FLUX.2 Klein）
    qwen/              # 画像生成・編集（Qwen Image）
    ideogram4/         # 画像生成（Ideogram 4、タイポグラフィ）
    ernie/             # 画像生成・編集（ERNIE-Image）
    seedvr2/           # 画像超解像（SeedVR2）
    depthpro/          # 深度推定（Depth Pro）
    acestep/           # 音楽生成（ACE-Step 1.5、別 venv のサブプロセス）
    audiogen/          # 効果音生成（AudioGen）
    ltx2/              # 動画生成（LTX-2）
    web/               # Web 検索/取得（SearXNG + Crawl4AI resident subprocess）

  api/                 # FastAPI routers。生成系は domain/family で編成
    chat/              # POST /v1/chat/completions
    embedding/         # POST /v1/embedding
    image/
      zimage/          # POST /v1/image/zimage/{generate,train}
      flux2/           # POST /v1/image/flux2/{generate,edit,train}
      qwen/            # POST /v1/image/qwen/{generate,edit}
      ideogram4/       # POST /v1/image/ideogram4/generate
      ernie/           # POST /v1/image/ernie/{generate,edit,train}
      seedvr2/         # POST /v1/image/seedvr2/upscale
      depthpro/        # POST /v1/image/depthpro/estimate
    audio/
      acestep/         # POST /v1/audio/acestep/{generate,cover,repaint,extract}
      audiogen/        # POST /v1/audio/audiogen/generate
    video/
      ltx2/            # POST /v1/video/ltx2/generate
    web/               # POST /v1/web/search, GET /v1/web/fetch
    files/             # POST/GET/DELETE /v1/files
    jobs/              # GET/DELETE /v1/jobs
    models/            # GET /v1/models, /v1/{domain}/{family}/models
    health/            # GET /health
    openapi            # GET /openapi.json, /v1/{domain}/{family}/openapi.json
```

---

## 起動フロー

```sh
アプリ起動
  → 各 capability の register() を呼ぶ
      → ModelSpec を model レジストリに登録（servable モデルのカタログ）
      → CapabilitySpec を capability レジストリに登録（OpenAPI の説明と docs URL）
  → api 側が各 router を FastAPI app に mount
  → warmup（セットアップ済みの KIAPI_WARMUP_MODELS を予算内で逐次ロードし常駐させる）
  → リクエスト受付開始
```

warmup は任意（既定は遅延ロード）で、指定モデルを起動時に確保・準備しておくことで初回リクエストのロード待ちをなくす。
warmup しないモデルは初回 `acquire` 時にロードされる。未セットアップの warmup 対象は
warning を出して skip し、サーバー起動は継続する。

---

## アプリ設定とユーザーディレクトリ

`core/app` は、アプリ全体の `AppContext` と、kiapi が使うユーザー別ディレクトリの
解決を担う。ユーザー別ディレクトリは下記の優先順で決定する。

| 用途 | 設定 | 環境変数 fallback | platformdirs |
|---|---|---|---|
| cache | `KIAPI_USER_CACHE_DIR` | `XDG_CACHE_HOME/kiapi` | `PlatformDirs(appname="kiapi", appauthor="kiarina").user_cache_dir` |
| config | `KIAPI_USER_CONFIG_DIR` | `XDG_CONFIG_HOME/kiapi` | `PlatformDirs(appname="kiapi", appauthor="kiarina").user_config_dir` |
| data | `KIAPI_USER_DATA_DIR` | `XDG_DATA_HOME/kiapi` | `PlatformDirs(appname="kiapi", appauthor="kiarina").user_data_dir` |

設定値で指定された `~` は、実行ユーザーの home directory として展開する。

---

## セットアップ管理

> [!NOTE] 重い初回ダウンロードを API 実行時に発生させないため、モデル重みや Docker image は事前に activate する。

各 `ModelSpec` は `setup_resources` を持つ。resource は、モデルを実行する前に
ローカルへ準備しておく必要があるディスク上の資源を表す。

| resource | 判定 | activate | deactivate |
|---|---|---|---|
| `hf_snapshot` | `snapshot_download(..., local_files_only=True)` が成功するか | Hugging Face から snapshot download | HF cache の該当 repo revision を削除 |
| `docker_image` | `docker image inspect` が成功するか | `docker pull` | `docker image rm` |
| `local_path` | path が存在するか | no-op | path を削除 |
| `python_venv` | venv の Python で検証 import が成功するか | `uv venv` + `uv pip install` | venv directory を削除 |

CLI:

```sh
kiapi status
kiapi activate
kiapi activate --all
kiapi activate --domain image --family chat --repo Qwen/Qwen-Image
kiapi deactivate --all
kiapi deactivate --domain image --family web --repo searxng/searxng:latest
kiapi run
```

`kiapi activate` は引数なしの場合、`questionary` の checkbox UI で model を選択する。
`kiapi deactivate` も引数なしの場合は checkbox UI で model を選択し、削除前に確認する。

API 実行時は、handler が `ctx.ensure_model_ready(spec)` を呼び、
未セットアップなら `SetupRequiredError` を投げる。router はこれを HTTP 503 に変換し、
`kiapi activate --repo ...` の実行ヒントを返す。

---

## 処理フロー

リクエストは、能力ごとの handler を Job として single-flight worker に投入して処理する。
GPU を使うモデルだけでなく、Web backend のような常駐 subprocess も同じ acquire/release
の流れに乗る。

### 推論系 API（sync）

```sh
リクエスト
  → api router          # リクエストを検証し params を組み立て、Accept を見る
  → submit_and_maybe_wait
  → worker（単一スレッド + キュー）  # 1 ジョブずつ直列実行
      → memory.acquire(model)         # 期限切れ掃引 → 予算判定 → 退避/ロード
      → capability handler            # 生成。ProgressReporter で進捗更新
      → files.put(...)                # 成果物を Files に保存（job.artifacts = [file_id]）
  → 完了待ち（KIAPI_SYNC_TIMEOUT_S 超過でエラー）
  → レスポンス          # 単一成果物 → 生バイト（+ X-Kiapi-File-Id / -Job-Id ヘッダ）
                        # 複数 or Accept: application/json → Job JSON
```

### 推論系 API（async）

```sh
リクエスト（mode=async）
  → api router → worker にジョブ投入
  → 即レスポンス        # 202 + job_id（待たない）
                        ┊
  worker が裏でジョブ実行（sync と同じ acquire → 生成 → files.put）
                        ┊
クライアントがポーリング
  → GET /v1/jobs/{id}   # status / progress / progress_label を観測
  → GET /v1/files/{id}  # 完了後に成果物メタ・本体を取得
```

### Web API

```sh
リクエスト
  → api router
  → Job 作成
  → worker（単一スレッド + キュー）
      → memory.acquire(web:search | web:fetch)
          → 初回のみ docker run --rm を foreground subprocess として起動
          → 動的 localhost port の healthcheck を待つ
      → capability handler  # resident backend へ sync HTTP
      → fetch は files.put(...) に保存
  → レスポンス          # search は JSON、fetch は raw body（+ file/job headers）
```

SearXNG / Crawl4AI は Docker container そのものとしてではなく、kiapi が所有する
resident subprocess の payload として扱う。起動コマンドが `docker run --rm` なので、
kiapi 停止や eviction で subprocess を止めれば container も掃除される。

## Remote Job Relay

relay は別パッケージ `kiapi-relay` にあり、`KIAPI_RELAY_DEFAULT` または
`kiapi run --relay ...` で有効化する optional background subsystem である。
`kiapi_relay` は安定した `Relay` / `RelayDelivery` protocol、request client、および
plugin registry を定義する。`kiapi_relay.gcp` は GCP transport、`kiapi_relay.local` は
local verification 用の filesystem-backed transport を実装する。`kiapi-proxy`
パッケージは同じ `kiapi_relay` の request client を使い、HTTP リクエストを relay 経由で
kiapi インスタンスに転送する。

```text
requester
  → GCS request.json
  → RTDB request notification
      ┊
GCP relay SSE listener
  → RTDB queued
  → local relay queue
  → RTDB running
  → process 内 FastAPI app へ ASGI dispatch
  → GCS response.body（binary のみ）
  → GCS response.json（create-only generation precondition）
  → atomic RTDB terminal response + request deletion
```

listener は delivery processing と独立して動作するため、現在の request を実行中でも次の
request を local queue に積める。relay runner は delivery を直列に消費する。GPU job の
直列化は API worker が引き続き管理し、relay progress は内部 job state ではなく bridge
の進捗を表す。

RTDB には Google OAuth credential を使う REST streaming API でアクセスする。terminal
delivery は root-level multi-location `PATCH` を使い、response 公開と request 削除を
atomic に行う。GCS は body、metadata の順で公開する。`response.json` が commit marker
であり、`if_generation_match=0` を使用する。

queued delivery の消費時に `response.json` が存在する場合、content type と size を復旧し、
terminal RTDB notification を再送して API dispatch を skip する。これにより、完了済み
処理を意図的に繰り返さず at-least-once notification handling を実現する。同じ node ID の
kiapi process が複数あれば実行は重複し得るが、GCS commit marker を作成できるのは 1
process だけである。

LocalRelay は GCP の layout を local root directory 配下に写す。
`{root}/{prefix}/nodes/{node_id}/requests/*.json` を poll し、
`sessions/{session_id}/request.json` から request を読み、`response.body` を
`response.json` より先に書き、terminal status を書いたタイミングで request notification
を削除する。

---

> [!NOTE] 以降は、上記の各ステップを実現する仕組み。

---

## モデル

> [!NOTE] 全能力のモデルを単一のカタログ（レジストリ）で扱い、メモリ予算・解決・発見の起点にする。

各モデルは `ModelSpec` として model レジストリに登録される。主なフィールド:

| フィールド | 意味 |
|---|---|
| `name` / `aliases` | モデルの識別子（`model` で指定する名前 = バリアント名のみ） |
| `family` / `domain` | 所属ファミリーとモダリティの括り（解決・ルーティングに使う） |
| `modalities_in` | 受け付ける入力モダリティ（text / image / audio / video） |
| `weight_gb` / `peak_headroom_gb` | 常駐重みと実行時ピークの見積り（メモリ予算が使う） |
| `framework` | クリーンアップ方式の選択（mlx / torch / 別プロセス等） |
| `resident` | 常駐型か一時型か（下記） |
| `ttl_seconds` | idle TTL（未設定はグローバル既定を継承） |
| `priority` / `default` | 退避優先度（高いほど残る）/ ファミリー既定モデルか |

- **解決**: `resolve(family, model)` でファミリー内のバリアントを引く。`model` 省略時は
  `default` を使う。
- **常駐型 / 一時型**:
  - **常駐型（`resident=True`）** — `acquire` でロードし、TTL/退避まで常駐させる。
    通常のモデル。
  - **一時型（`resident=False`）** — 1 回の生成のためにロード→実行→即解放する。
    巨大で常駐に向かないもの（ltx2）や、ロード時に量子化/LoRA を焼き込むため常駐
    モデルを使い回せないケース（zimage の LoRA・quantize 指定）。予算は `acquire`
    ではなく `memory.reserve()` でピーク分だけ確保する。
- **モデルの追加 = 1 モデルモジュール（`_models/<model>.py`）+ 1 registry 行**。
  生成処理（プロンプト構築・メディア処理・サンプリング・後処理）は各モジュールに
  分割して持つ。能力ごとの詳細は各 `capabilities/{family}/README` を参照。
- **発見**: `GET /v1/models` は chat 専用（OpenAI 互換）、それ以外は
  `/v1/embedding/models` / `/v1/{domain}/{family}/models` で一覧できる。

---

## メモリ管理

> [!NOTE] 非機能要件「メモリを管理し破綻させない」を担う。

複数の能力にまたがる全モデルが、単一のグローバル予算 `KIAPI_MEMORY_LIMIT_GB` を
共有する。`KIAPI_MEMORY_LIMIT_GB` が未指定の場合は、起動時に搭載メモリの 80% を
実効予算として自動設定する。指定されている場合はその値を尊重する。値決定後、
現在の空きメモリが実効予算を下回っている場合は warning を出す。
**常駐物（resident weights）** と **実行時ピーク（peak headroom）** を分離して管理する。

- 各常駐物は `(key, size_gb, priority, last_used, release_fn)` を登録する。
  `priority` は既定 0。**値が小さいほど先に退避される**ため、小さく常駐させ続けたい
  モデルには高い priority を与えて保持する。
- 全体シングルフライト（同時 1 ジョブ）なので、考慮すべき実行時ピークは常に
  1 ジョブ分のみ。ジョブ開始時の予算チェックは:

  ```
  Σ(常駐 weight − このジョブが使うモデル分)
      + このジョブの model weight + このジョブの peak_headroom  ≤  MAX
  ```

- 不足時は **`(priority 昇順, last_used 昇順)`** の順で `release_fn` を呼んで退避する
  （「優先度が低いもの ＞ 使ってない順」）。
- `release_fn` はフレームワーク別のクリーンアップを担い、MLX と PyTorch/MPS の混在を
  吸収する:
  - MLX 系: `del refs` → `gc.collect()` → `mx.clear_cache()`
  - PyTorch/MPS 系（acestep 等）: 加えて `torch.mps.empty_cache()`
- `size_gb` はレジストリの推定値から始め、初回ロード後に実測（`mx.get_active_memory`
  差分等）で補正する。
- 起動時 warmup するモデルは `KIAPI_WARMUP` / `KIAPI_WARMUP_MODELS` で指定する
  （予算内で逐次ロード。既定は遅延ロード）。

---

## TTL（idle 自動解放）

> [!NOTE] 連続使用時の応答速度と、放置時のメモリ解放を両立する。

各モデルは任意で idle TTL を持つ（`ttl_seconds`、未設定はグローバル既定
`KIAPI_DEFAULT_TTL_S` を継承、`0`/負値で「無期限＝ピン」）。TTL を過ぎた常駐モデルは
2 つのトリガで解放される:

1. **リクエスト時** — `acquire` の冒頭で期限切れモデルを掃引してから予算判定（対象
   モデル自身は除外）。
2. **アイドル時** — バックグラウンドの定期掃引（`KIAPI_TTL_SWEEP_INTERVAL_S`）。

掃引は必ず単一 worker スレッド（共有 executor）で実行し、生成と直列化・MLX の
スレッド固有性を守る。再使用のたびに `last_used` が更新され idle はリセットされる。
`GET /health` は各モデルの `idle_s` / `ttl_s` / `expires_in_s` を表示する。

---

## ジョブ / ワーカー

> [!NOTE] 非機能要件「GPU 処理をキューイングして 1 つずつ実行」を担う。

全処理はグローバルな `ThreadPoolExecutor(max_workers=1)` + キュー上で実行され、
**全体で同時 1 ジョブ**に直列化される（MLX のスレッド固有性を守り、予算会計を単純に
保つ）。並列が必要なら **kiapi を複数プロセス起動**し、用途別に MAX メモリを分割する。

- **同期・非同期を常にジョブ化**し、生成系は `mode`(sync/async) で指定する。
  - async は即座に `job_id` を返す。
  - sync はジョブ完了を待つ。**時間超過したらエラー**を返す（非同期へフォール
    バックしない）。
- Chat / Embedding は **async 受付なし**（内部的にはジョブ化する）。
- **streaming は Chat のみ**（`stream=true` で SSE）。実行自体は同じ単一 worker 上で
  直列化される。
- **キャンセル（`DELETE /v1/jobs/{id}`）**: queued は除去できるが、実行中の生成処理は
  中断不可（ベストエフォート）。

### ジョブモデル

```
Job:
  id: str
  type: str          # 例 "chat" | "embedding" | "acestep.generate" | ...
  status: str        # queued | running | succeeded | failed | canceled
  params: dict       # 入力パラメータ（再現用）
  result: dict       # type ごとに自由形式（成果物メタデータ）
  artifacts: [file_id]
  error: str | None
  created_at / started_at / finished_at
  progress: float | None       # 実行中の進捗 [0,1]、未報告は None
  progress_label: str | None   # 現フェーズの短いラベル（例 "denoising"）
```

---

## 進捗報告

> [!NOTE] 非機能要件「非同期タスクの進捗を把握できる」を担う。

進捗の配管は **ambient（contextvar）** で行う。全体シングルフライトなので「現在
実行中ジョブの進捗レポータ」は一意に定まる。worker は実行直前に `ProgressReporter`
をワーカースレッド上の contextvar に束ね、capability コードは
`ProgressReporter.current()` で `update(fraction, label)` / `step(i, total)` を呼ぶ。
未束縛時の `current()` は**サイレント no-op** を返すため、呼び出し側は条件分岐なしで
報告でき、router/handler のシグネチャも変えずに済む。`GET /v1/jobs/{id}` で観測する。

- image 系（mflux）は per-step 進捗に対応（デノイズループフックに共有コールバックを
  冪等登録）。depthpro はループの無い単一フォワードのため粗い進捗のみ。
- 更新は時間・差分でスロットリングする。

---

## ファイル管理

> [!NOTE] 成果物をジョブより長命に保ち、`file_id` で参照可能にする。

統一 Files API。`file_id` で管理し、メタデータは自己記述的（seed・params・timings を
サイドカーに保持）。ジョブの artifacts は `file_id` で参照する。**ファイルはジョブより
長命**（ジョブはインメモリでプロセス再起動時にクリアされるが、Files API の保存先に
残っている限り `file_id` で取得できる）。生成系の入力ファイルも file_id 参照で受け取る。

既定の保存先は `KIAPI_FILES_ROOT=/tmp/kiapi/files`。これは運用時に生成物やアップロードが
溜まり続けるのを避けるためで、OS の再起動や tmp cleanup で消える可能性がある。成果物を
長期保存したい場合は、`KIAPI_FILES_ROOT=~/.kiapi/files` や外部ディスク上のディレクトリを
指定する。

リクエスト処理中だけ使う中間ファイルは `KIAPI_TMP_ROOT=/tmp/kiapi/work` 以下に、
`chat/qwen3_omni/{entry}` や `image/zimage/{entry}` のような目的別ディレクトリを作って
保存する。モデル重みやライブラリキャッシュは Hugging Face、mflux、Docker など各
ライブラリ・ツールの管理下に置き、kiapi の Files API / workdir とは分けて扱う。

---

## sync レスポンスのネゴシエーション

> [!NOTE] sync 利用を「ファイルが直接落ちてくる」体験にする。

生成系の sync レスポンスは、**成果物が単一なら既定でその生バイト列を直接返す**
（`curl -o out.png .../generate` がそのまま機能する）。

- `file_id` / `job_id` はヘッダ `X-Kiapi-File-Id` / `X-Kiapi-Job-Id` に載せ、
  seed・params・timings 等の全メタは後から `GET /v1/files/{id}` で取得できる。
- `Accept: application/json` 指定時・成果物が複数（例: acestep `extract`）・async
  （`202`）の場合は Job dict（JSON）を返す。
- 実装は `api/_helpers/submit_and_maybe_wait.py` に集約され、各生成エンドポイントが
  `Accept` ヘッダを渡す。chat/embedding はこの封筒処理を通らない。

---

## API 編成（domain / family / op）

> [!NOTE] 操作空間が収束しているかどうかで API の形を変える。

- **chat / embedding は標準モダリティ API**（`POST /v1/chat/completions`,
  `POST /v1/embedding`、`model` で互換差し替え）。業界が OpenAI 形式に収束し操作が
  単一なので共通 API が成立する。
- **生成系はプロバイダ（ファミリー）軸** `POST /v1/<domain>/<family>/<op>`。モデルに
  よって「できる操作」が大きく異なる（acestep は cover/repaint/extract を持つが
  audiogen は generate のみ）ため、共通スキーマで削らず各ファミリーが**自分の操作
  語彙と request 形をそのまま**出す。
  - `domain` — モダリティの括り（audio/video/image）。発見性・グルーピング用。
  - `family` — upstream のパッケージ/モデル名を正規化した区切り無し小文字の識別子。
    **dir == family** で常に一致（alias は設けない）。
- **エンドポイントを分けるか model に押し込むかの基準**: エンドポイント = 操作の
  語彙、`model` = その語彙を丸ごと同じに満たす差し替え可能なバリアント（`model` 名は
  バリアント名のみ、ファミリー名を繰り返さない）。
  - acestep `xl-base` / `turbo` は同じ 4 操作を同じ形で満たす → 同一ファミリー、
    `model` で選択。
  - acestep vs audiogen は語彙が違う → 別ファミリー = 別エンドポイント。
- **横断的な「封筒」は統一**: 全生成は `mode` を受け Job を返し、成果物は
  `artifacts:[file_id]`、入力は file_id 参照、エラーコード体系・capability 別 OpenAPI・
  `/v1/{domain}/{family}/models`・auth・メモリ予算・全体シングルフライトは共通。
  **封筒 = 共通、payload = ファミリー固有**。

`model` によるバリアント解決とレジストリの詳細は「モデル」の節を参照。

---

## resident subprocess model

> [!NOTE] プロセス外に常駐する能力も、モデルと同じ acquire / release / TTL の流れに乗せる。

一部の能力は、Python オブジェクトとして重みをロードするのではなく、別プロセスを
起動してそのプロセス状態を resident payload として保持する。

- **acestep** — 専用 venv の Python subprocess を起動し、ACE-Step の LLM + DiT を常駐。
- **web/search** — `docker run --rm searxng/searxng` を foreground subprocess として起動。
- **web/fetch** — `docker run --rm unclecode/crawl4ai` を foreground subprocess として起動。

core から見ると、いずれも `ModelSpec.module.load(spec) -> payload` と
`release(payload)` を持つ resident model である。Docker は web module の実装詳細であり、
起動時に空いている localhost port を選び、healthcheck 完了後にその `base_url` を payload
として handler が使う。

---

## 依存ライブラリ不一致の回避（acestep の venv 分割）

> [!NOTE] 1 つの venv に同居できない依存を、サブプロセスとして隔離しつつ統一管理下に置く。

多くの能力は `transformers` 5.x 系で 1 つの venv に同居できるが、**acestep
（ace-step）は `transformers` 4.x を要求**し、chat の mlx-vlm / embedding の
mlx-embeddings（いずれも 5.x 要求）と同一プロセスに同居できない。競合は transformers
のみで、mlx / torch は互換。

- chat / embedding / 他の生成系は kiapi 本体の venv（transformers 5.x）に統合する。
- **acestep は専用 venv の常駐ワーカープロセスとして実行**し、
  `kiapi activate --family acestep` で `python_venv` resource として構築する。
  既定では venv / project / checkpoints を `core/app` の user data dir 配下の
  `acestep/` に置く。
  kiapi 本体はこれをメモリマネージャの**常駐エントリ**として扱う（`release_fn` =
  プロセス終了）。統一ジョブ / ファイル / メモリ予算 / 全体シングルフライトを維持した
  まま依存衝突を隔離する。なお acestep は別プロセスだが GPU 推論を行うため**推論型**
  であり、予算・TTL の管理下に置く（「別プロセスか否か」ではなく「推論か否か」で
  分類する）。
- IPC は行指向 JSON（stdin/stdout）+ 生成物はファイルパス受け渡し。実装詳細は
  [acestep/README.ja.md](kiapi/capabilities/acestep/README.ja.md) を参照。

---

## OpenAPI

> [!NOTE] 非機能要件「API サーバー自体が LLM に使い方を説明できる」を担う。

kiapi は `GET /openapi.json`（ナビゲーション層）と
`GET /v1/{domain}/{family}/openapi.json`（操作層）の 2 層で機械可読な説明を返す。
旧 `GET /v1/help` / `GET /v1/help/{family}` は廃止し、説明は OpenAPI に統合する。

エージェントの想定動線は次の通り：

1. `GET /openapi.json` → capability 一覧、docs URL、共通 endpoint を読む。
2. 目的に合う capability の `openapi.json` → `info.description`、operation
   description、request/response schema を読んで実際に呼ぶ。

- **root OpenAPI（"何ができて次にどこを見るか"）**：
  root は共通 endpoint と capability 別 docs へのリンクを持つ。各 capability の説明は
  `CapabilitySpec.summary`（1 行）から生成する。
- **capability OpenAPI（"実際の使い方"）**：
  `CapabilitySpec.description` を `info.description` に入れる。これは Markdown 形式の
  詳細説明で、モデル選び、全体 TIPS、例、注意点などを書く。endpoint の一覧は
  OpenAPI paths から、request parameter の構造と細かい値は Pydantic schema から
  自動生成されるため、個別 endpoint 依存の説明は endpoint docstring と
  request/response schema に置く。

`CapabilitySpec.summary` はタスク指向の 1 行にする。タスク → family のマッピングが
成立するかはこの文の質に懸かる（例：`acestep`=音楽生成 と `audiogen`=効果音 を
1 行で区別できること）。
