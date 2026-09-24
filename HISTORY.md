# HISTORY

完了した作業、実測値、過去の意思決定の記録です。
作業日を含めて、新しいものを上に追記します。

## 2026-09-24 — chat に Qwen3.8-Flash-Next を追加した

- `qwen3.8-flash-next`（`mlx-community/Qwen3.8-Flash-Next-4bit`、`model_type: qwen4_exp`、125B MoE・6B active）を追加。
  alias は `qwen3.8-flash`、`flash-next`、`qwen4_exp`。既定モデルと既存 alias（`qwen3.8` / `vlm` など）は変えていない
- 生成は `qwen3_5` handler をそのまま使う（chat template・Hermes/XML の tool call・thinking の切り替えが同じ）。
  load だけが違い、n-gram 表（PLE、約 32 GB）を mmap にする view をユーザーの cache dir（`chat/external-ple/`）に作る。
  非 PLE の重みは snapshot への symlink、`ple-store.json` は snapshot 内の byte 範囲を指すので、重みのコピーはない。
  mapped PLE が 128 shard を開くので、load 時にプロセスの open-file の soft limit を 65536 へ上げる
- 事前評価（labs `2026/09/24/qwen38-flash-next-reap-eval`、`2026/09/24/qwen38-flash-next-ple-mmap`、サーバー機
  Mac Studio M4 Max 128GB）: PLE を常駐させると 111.5 GB で 32K から Metal OOM。mmap にすると load 79.5 GB、
  needle 32K / 128K / 240K を全問正解（peak 83.6 / 89.9 / 96.0 GB、prefill 530〜580 tok/s）、エージェント 4/4、
  日本語 32/32、decode 約 40 tok/s（常駐時 47.1、Qwen3.8-27B 34.3）。expert を削った REAP-288 は日本語の知識が崩れたので不採用
- `weight_gb=79.5`、`peak_headroom_gb` は他の chat モデルと同じ 4 GB + APC 上限。240K 近い context と満杯の APC が重なると
  見積もりを超えうる（README に記載）
- サーバー機で chat の full verify（`verify_chat`・`verify_chat_omni_prefix`・`verify_chat_stream`）が全モデル通過。
  Flash-Next は text・max tokens・並列 tool call・tool_choice any / specific・parallel_tool_calls=false・continuation・画像を
  通常とストリーミングで確認した
- 観測: tool を渡して `tool_choice=auto` のとき、Flash-Next は「こんにちは」だけでも tool を呼びやすい
  （temperature 0 で `get_weather`、0.7 で 4 回中 3 回。1 回は引数が崩れた）。README に記載
- 未対応: 画像を追加したときの prefix 再利用（fork の `apc_image_prefix`）は `qwen3_5` 専用のまま。text の APC は
  upstream の実装で `qwen4_exp` にも効く。expert の SSD offload（`mlx_vlm/moe_offload.py`）は試していない
- ライセンスは Qwen Community License 1.0。商用の Model-as-a-Service / AI work assistant 事業には Qwen の別ライセンスが要る
  （外部に出さない内部利用は対象外）。README に記載

## 2026-09-20 — Omni の追加メディアで既存prefixを再利用する

- mlx-vlm fork `98300012bbccc728d0a98e92444cc45bc433e284`を実装・pinし、kiapiへ取り込んだ。
  上流PR [#2311](https://github.com/Blaizzy/mlx-vlm/pull/2311)はCI成功、review待ち。
  Qwen3.8画像対応[#2309](https://github.com/Blaizzy/mlx-vlm/pull/2309)に積み重ねた変更。
- 画像・音声・動画・混在・音声付き動画（既存demux方式）の追加で、変更のない履歴のKVを再利用し、
  追加mediaだけをencodeする。prefix内の処理済みcontent・grid・長さ・位置・FPSを識別する。
  Omniのdeepstackをfull-prompt座標へ合わせ、完全なRoPEを保持した。
- 複数音声をclipごとに特徴抽出・encodeし、長い音声の追加による過去clipのpadding変化を排除した。
  100-frame境界の長さ計算とchunk maskも修正。旧画像・同一path/同一長さの音声差し替え、FPS変更で
  対象mediaを再計算し、手前のtextだけを再利用することを確認した。
- 条件: Mac Studio M4 Max 128GB、macOS26.6.2、MLX0.32.2、Qwen3-Omni-30B-A3B-Instruct-4bit、
  temperature=0、APC4GiB、最大48生成tokens。各2回の中央値。TTFTはモデルloadを除き前処理を含む。

| 追加media | cold TTFT (s) | hit TTFT (s) | cached / prompt tokens |
|---|---:|---:|---:|
| image | 1.719 | 0.174 | 2709 / 2755 |
| audio | 1.783 | 0.230 | 2713 / 2793 |
| video | 1.891 | 0.287 | 2791 / 2920 |
| mixed | 2.035 | 0.359 | 2831 / 3011 |
| audiovisual | 1.997 | 0.357 | 2813 / 2990 |

- cold/hitの色・合言葉の順序と追加分のみencodeを実機確認。量子化MoEはprefill/encodeの形状によって
  logitsが完全一致しないため、小型float32実モデルでfull/restore/chunked logitsの一致も検証した。
- upstream cache/generate/prefix467件、モデル契約3件、kiapi CPU340件、旧engine互換55件、make成功。
  chat full verifyと具体的な内容anchorを検査するOmni HTTP5種も成功した。
  異なる画像を追加するstream検証は2,448tokensを再利用し、旧画像変更はcached=0で正しい色を返した。
- 曖昧な質問でUnderstood.だけ返す現象はcoldでも同じで、質問を具体化して実際の前回答を履歴に使う検証にした。
  Qwen用enable_thinking=FalseはOmniに流用しない。
- Native interleaved audio/videoとbatchは今回の対象外。公式0.7.1では従来の全media単位の識別へfallbackする。
  複数音声はforkが必要。Qwen3.8既存対応とprefill既定2048は維持。
- サーバー機へ依存を同期して再起動し、private network経由でもHTTP5種を全て確認した。
  cached tokensはimage105、audio432、video1833、audiovisual2228、mixed2291。最終healthはok、queue_len=0。
- 仕様はchat README、実機probeはmlx-vlm `examples/verify_omni_media_prefix.py`、API回帰は
  `scripts/capabilities/verify_chat_omni_prefix.py`。raw結果は`.verify/omni-prefix-98300012/`に保存。

## 2026-09-20 — Qwen3.8 の prefill chunk 比較を完了し既定2048を維持した

- 依頼範囲は`prefill_step_size`だけ。モデル・量子化・engine pin・画像APC方式・checkpoint間隔は変更せず、
  **既定2048を維持**した。512/1024の差は試行間のばらつき以下、大きいchunkは遅くメモリも増えた。
- 条件: Mac Studio M4 Max 128GB、macOS 26.6.2、MLX 0.32.2、Qwen3.8-27B-4bit、
  kiapi `3829991`、mlx-vlm fork `3c5bd17c`。APC 4 GiB、temperature=0、seed=42、text生成1 token。
  モデルloadを除外し短いwarmup後に測定。各cold試行前にAPC/MLX allocation cacheをclear。
  前処理とcheckpoint保存を含む最初のengine tokenまでの時間で、HTTP/SSEの転送時間は含まない。
- 各条件2回、2回目は逆順。前日に別GPUアプリが起動して汚染された16Kの試行は使わず、全条件を再測定した。
  再測定中は競合するGPU作業を観測せず、swap使用量0。通常のdesktop appsは開いたまま。

16,402 prompt tokens。TTFTは2回の中央値、peakはMLXが計測したモデル重み込みの最大値（decimal GB）。

| Chunk tokens | TTFT (s) | MLX peak (GB) |
|---|---:|---:|
| 512 | 67.397 | 21.01 |
| 1024 | 67.027 | 21.01 |
| 2048 | 67.073 | 21.66 |
| 4096 | 67.790 | 25.44 |
| 8192 | 69.412 | 33.11 |

- 1024の2048に対する差は約0.07%。1024自身の試行差は0.256秒あり、改善として採用しない。
  8192は約3.5%遅く、peakが約11.45 GB増えた。
- 別入力の4,114 tokensでは128=16.741秒、256=16.363秒、2048=16.271秒（各2回中央値）。
  小さくする方向にも速度の利点なし。前日完了分の512〜8192も約16.0〜16.3秒だった。
- 画像検証は512/2048/8192の各2回で、同一request再送、画像追加、旧画像変更、cold対照を全て通過。
  赤→青の画像追加は4,331 prompt tokensのうち4,210を再利用し、TTFT中央値は約0.679〜0.680秒。
  coldは約17.05〜17.24秒。赤を緑へ変更したケースはcached_tokens=0で`Green, Blue`を返し、
  unchangedのcold/hitは`Red, Blue`を返した。
- 画像promptは4,211/4,331 tokensで、8192指定時もcheckpoint境界により実chunkは最大4096。
  16K textでは実際に8192 chunkを処理したことをhistogramで確認。より長い入力・別モデルの最適値は断定しない。
- 再利用する計測手順は[playbook](docs/playbooks/chat-prefill-benchmark.md)、
  scriptは`scripts/capabilities/measure_chat_prefill.py`。生データは同playbookからリンクする。
  scriptは前日の`make`とCPU tests 339件が通過した版から変更せず、今回GPUの全計画を完走した。
  productionコード・設定・依存を変更していないため、通常chat full verifyの重複実行は不要と判断した。

## 2026-09-19 — Qwen3.8 で新しい画像を追加しても既存prefixを再利用できるようにした

- ユーザー合意に基づきmlx-vlm本体で実装し、fork commit `3c5bd17c5cff3ad45d80273b366e86ad7df4ed96`を
  kiapiの`tool.uv.sources` / uv.lockへ固定した。上流PR: [Blaizzy/mlx-vlm#2309](https://github.com/Blaizzy/mlx-vlm/pull/2309)。
  上流CIは成功し、review / merge待ち。通常のPyPI依存は0.7.1のまま維持し、新引数がない場合は旧方式へfallbackする
- kiapiはQwen3.8だけ`apc_image_prefix=True`を内部指定する。request APIは変更しない。
  Qwen3.6 / Omniのmedia追加は従来どおりwhole-request invalidation。diskは有効化していない
- forkは処理済みpixel / grid / token spanを画像ごとにhashし、checkpoint以前の画像だけをkeyへ含める。
  checkpoint範囲ごとに既存exact-cache APIを検索するため保存形式は変わらない。
  画像途中にはcheckpointを置かず、再開時は新しい画像だけをencodeし、full-prompt RoPEを保持する
- 位置・特徴量・embedding・mask・cacheのopaque override、投機的decode、KV量子化/size overrideは
  新しいopt-in経路でAPCを無効化する。単一requestのqwen3_5 text/image限定で、continuous batchingは対象外
- Mac Studio M4 Max 128GB、Qwen3.8-27B-4bit、temperature=0、memory APC 4 GiB、最大20生成tokens。
  forkの`examples/verify_image_prefix_apc.py`で実測。モデルloadを除き前処理を含む最初の出力までの時間（各1回）:

| 入力 | Prompt tokens | 再利用tokens | Cold TTFT | Prefix hit TTFT |
|---|---:|---:|---:|---:|
| text履歴 + 1画像 | 2,920 | 2,822 | 11.586 s | 0.644 s |
| 画像履歴 + 1画像 | 2,995 | 2,897 | 11.869 s | 0.648 s |
| 画像履歴 + 2画像 | 3,061 | 2,897 | 12.139 s | 0.924 s |

- 期待する色の順序はcold/hitで一致。first-token分布のKL divergenceは0.0005未満。
  量子化の数値差があるためbit一致は保証しない。encodeしたpatch行数を計測し、追加画像だけの処理を確認した
- 同じpathの旧画像差し替え、画像の順序変更、grid/tenant変更を検証。旧画像を含むcheckpointは使わず、
  前段textの2,048 tokensだけを再利用できた。API側でも縦横比が異なる画像の追加を確認した
- 旧画像変更のAPI検証で古いassistant回答Red.を残したところ、cached_tokens=0でも誤答した。
  cache.clear後も同じ回答だったためcache問題ではなく矛盾した検証入力の問題と切り分け、入力を修正した
- fork baseにはOmniのC/H修正も含まれる。Cはno-op、Hはexpanded deepstackを検出してskipし、
  公式0.7.1向けのcompact-row互換処理を残した。再利用方針と制約はchat READMEを更新した
- upstream cache/generate/画像prefix test 451件 + model contract 2件、kiapi make / CPU test 339件、
  通常chat全caseとstream全caseが通過。公式0.7.1環境でもchat CPU test 54件が通過した。
  kiapiの45画像/2,991 tokensのmatrix、media追加、旧画像変更、clear/reloadも通過し、
  release後のMLX active memoryは1,056 bytesだった
- 本番checkoutへpinを反映し、Tailscale経由のAPIで画像追加時に2,499 tokensを再利用、
  旧画像差し替え時はcached_tokens=0で正しい色を返すことを確認した。詳細な配置・運用記録は運用側に残す。


## 2026-09-19 — Omni と画像・音声・動画の chat APC を実装・検証した

- Qwen3.6 / Qwen3.8の画像入力と、Qwen3-Omniのtext / image / audio / video / image + videoへ
  memory-only APCを広げた。モデルごとのmanager、無効化設定、cached_tokens、キャンセル時のclearを共通化した
- Omniではmlx-vlm 0.7.1のAPC境界判定にthinker内のimage/video/audio token IDが欠け、
  warm imageでfull media gridをtrim済みsuffixへ当ててIndexErrorになることを再現した。
  専用patchで境界判定を補完し、復元後のtext suffixはmediaを再encodeせずfull-prompt RoPEを保持する。
  Omniのcacheはlayer-major snapshotを用い、patch C / Hとの組み合わせを長いvisual promptで確認した
- mediaは種類ごとの順序付きSHA-256内容hashとfps/use_audio_in_videoをcache identityへ含める。
  同じ内容の別pathは同じkey、同じpathで内容変更は別keyとなることをCPU testで確認。
  実機でも毎回異なる一時pathでhitし、赤→緑の画像変更ではmissして正しい色を応答した。
  fps / video audio設定変更と、新しいmediaをsuffixへ追加した場合はwhole-request cold fallbackする
- 通常のtext suffixはpartial hitできる。Qwen3.6の短い画像会話は、新規assistant用の空think prefillが
  履歴中では消えるためcheckpointとprefixが一致せずcoldになる場合がある。同一requestの再送はhitする。
  上流processorの複数audio clip/request非対応も確認し、READMEへ明記した
- APCのclear / model release / reloadを検証し、各モデルの解放後にMLX active memoryが約1 KiBまで戻ること、
  再ロード後のcached_tokensが0になることを確認。単なるheadroom予約ではidle modelのcacheが未計上だったため、
  thread-safeなresident_extra_bytes hookでhealth・eviction・transient reservationへ算入した。
  active modelのheadroomも固定20 GiBから、APC設定上限 + 4 GiB（無効時4 GiB）へ変更した
- `scripts/capabilities/measure_chat_apc.py`を追加。Mac Studio M4 Max 128GB、mlx-vlm 0.7.1、
  temperature=0、seed=42、最大64生成tokens、APC上限4 GiB。モデルロードと初回text kernel warmupを除外し、
  前処理を含む最初のcontent出力までの時間を計測。warmは同一request 3回の中央値。
  cold/warmの回答を比較し、画像の色・形、動画の場面、音声の主題が維持されることを確認した。
  音声等の自由記述は浮動小数点差による言い回しの差があり、文字列完全一致を保証しない

| Model / input | Prompt tokens | Cold TTFT (s) | Warm median (s) | Cached tokens |
|---|---:|---:|---:|---:|
| Qwen3.8 text | 2,128 | 8.290 | 0.075 | 2,127 |
| Qwen3.8 image | 86 | 0.496 | 0.072 | 85 |
| Qwen3.8 long image | 2,991 | 12.716 | 0.165 | 2,990 |
| Qwen3.6 text | 2,128 | 8.359 | 0.075 | 2,127 |
| Qwen3.6 image | 86 | 0.500 | 0.073 | 85 |
| Qwen3.6 long image | 2,991 | 12.814 | 0.177 | 2,990 |
| Omni text | 2,124 | 1.310 | 0.115 | 2,112 |
| Omni image | 82 | 0.198 | 0.052 | 80 |
| Omni long image | 2,987 | 2.879 | 0.185 | 2,976 |
| Omni audio | 408 | 0.821 | 0.223 | 400 |
| Omni video | 3,602 | 4.018 | 0.563 | 3,600 |
| Omni image + video | 3,670 | 4.051 | 0.595 | 3,664 |

- Disk tierは`measure_chat_apc_disk.py`で別評価し、採用しないと判断した。
  Qwen3.8 / 3,028 prompt tokensのmemory cold 11.941 s、memory warm 0.078 s、disk reopen 0.115 s。
  diskを有効にしてもmemory hitは0.078 sで追加効果がなく、効果はeviction / restart後の再利用となる。
  約640.5 MBのsafetensorsには復元可能なtoken IDsが平文metadataとして含まれる。
  通常の破損headerはcold fallbackし、1 KiB capではflush後0 bytesへevictされたが、capはnamespace単位の
  事後制限で、canonical filenameのheaderをJSON arrayにするとTypeErrorがfallback外へ漏れた。
  kiapiはDiskBlockStoreを作らず、APC_DISK_*環境変数でも永続化を有効にしない

- full verifyの出力確認で、parallel_tool_calls=falseでも2件目のtool名だけ先行送信する既存不具合を発見した。
  名前の送信にも同じ件数制限を適用し、JSON/HermesのCPU regression testと3 modelのstream検証を追加した。
- `make`、CPU test 336件、chat full verify（全model・全modality・stream/non-stream）、
  修正後の3 model stream専用検証が通過した。稼働・キャッシュ破棄の追加確認は運用側の記録を参照。


## 2026-09-19 — chat client切断をjob cancellationへ結線した

- 既存の`JobStatus.CANCELED` / `Job.mark_canceled()`を実処理へ結線した。Jobにthread-safeなcancel signalを
  持たせ、workerはqueued jobを開始前にskipし、協調キャンセル例外を`failed`ではなく`canceled`へ遷移させる
- streamはSSE iteratorの`CancelledError`、non-streamは`Request.is_disconnected()`の監視からcancelを要求する。
  sync timeoutは従来どおり別扱いで、504後もjobを続ける
- Qwen3.6 / Qwen3.8 / Omniのgeneration iteratorをcancel-aware wrapperで包み、生成token境界で停止する。
  generatorをcloseし、temporary directoryとMLX cacheを解放する。APC hit中の早期closeはmlx-vlm内部の
  block lease解放まで到達しないため、キャンセル時だけ対象modelのAPC全体をclearする
- 実機Qwen3.8でstream / non-stream切断がともに`canceled`となり、`queue_len=0`へ戻ることを確認。
  3,248-tokenのAPC warm requestは0.089秒で出力開始後に切断でき、その後の同一promptが
  `cached_tokens: 0`でcold再計算（12.985秒）となり、安全にcacheを破棄できた
- mlx-vlm 0.7.1はchunked prefill中のcancel callbackを公開していないため、cold long promptは最初の
  generation tokenが返るまで止められない。100K tokens級では重要なので独立taskへ分離した
- `make`、unit test 318件、サーバー機のchat full verifyとstream usage検証が通過した

## 2026-09-19 — chat response に cached tokens をOpenAI互換で追加した

- non-stream responseの`usage.prompt_tokens_details.cached_tokens`へ、mlx-vlmが返すAPC再利用token数を追加した。
  `prompt_tokens`は従来どおり論理prompt全体で、cache miss、APC無効、非対応model / modalityは0を返す
- requestに`stream_options.include_usage`を追加した。trueの場合は`[DONE]`直前に、同じstream id、
  `choices: []`、最終usageを持つOpenAI互換chunkを返す。false / 未指定時のstreamは従来どおり
- OpenAPI、chat README、stream verifyを更新。`make`、unit test 312件、サーバー機のchat full verifyが通過した
- 実機のwarm Qwen3.6 streamで`prompt_tokens: 822`、`cached_tokens: 821`を確認。APC対象外の
  Qwen3-Omniは同じusage chunkで`cached_tokens: 0`を返すことを確認した

## 2026-09-19 — chat の長い text prompt に Automatic Prefix Caching を導入した

- mlx-vlm 0.7.1 の `APCManager` を Qwen3.6 / Qwen3.8 のmodel payloadごとに保持し、statelessな
  OpenAI-compatible requestでも、system message・tool schema・conversation historyの最長一致prefixを
  request横断で再利用するようにした。response自体はcacheしない。Qwen3-Omniと画像入力は安全性を
  個別検証するまで明示的に対象外
- memory-onlyで既定有効。1 modelあたり2048 blocks × 16 tokens、推定4 GiBを上限とし、diskへpromptを
  永続化しない。tenantはclient headerではなくserver設定の固定salt。model eviction / TTL / server shutdownで
  managerをcloseし、通常のMLX cacheとともに解放する。無効化すると従来のcold generationへ戻る
- Mac Studio M4 Max 128GB、mlx-vlm 0.7.1、Qwen3.8-27B-4bit、生成1 tokenで実測。25,252 prompt tokensの
  実装前content TTFTは108.102秒 / 108.808秒（中央値108.455秒）。実装後coldは109.295秒、同一promptの
  warm 3回は0.141 / 0.140 / 0.141秒（中央値0.141秒、約769倍、99.87%短縮）、25,251 tokensを再利用した
- 同じ長いhistoryに異なるuser suffixを追加するpartial hitでは、約25,255 tokens中24,576 tokensを再利用し、
  TTFTは3.679 / 3.504 / 3.509秒（中央値3.509秒、実装前比約30.9倍、96.76%短縮）。cache residentは
  約3.57 GB、観測peakは同一promptで23.37 GB、partial hitで24.93 GBだった
- `cached_tokens`、`prompt_tps`、peak memory、resident bytes、hit/miss集計はserver logへ出す。
  `usage.prompt_tokens`はcache hit後も論理prompt全体（25,252）のまま維持した
- `make`、chat unit test 29件、サーバー機のchat full verify（全case + stream専用検証）が通過。
  stream/non-stream、tool choice、parallel tool calls、画像、Omniのaudio/videoを含む既存経路を確認した
- Qwen3-Omniとmultimodal APC、disk tierは効果と安全性を独立して判断する。Omni / media hash / patch C・Hとの
  組み合わせは未検証なので、別taskへ分離した
- 本番のAPC上限を4 GiBから16 GiBへ変更し、Qwen3.6 / Qwen3.8の`peak_headroom_gb`を4から20へ
  引き上げた。model weightとは別にAPC最大16 GiBと従来の生成margin 4 GBを予約し、他modelとの
  共存・eviction判断でprefix cacheを無視しないようにした。通常はQwen3.6 / Qwen3.8の片方だけを使う

## 2026-09-16 — chat の出力上限をサーバーの cap から context window に替えた

- 意思決定（ユーザーと合意）: kiapi は個人利用が前提なので、どこまで出力させるかは呼び出し側が決める。
  サーバー全体の `max_tokens_cap`（`KIAPI_CHAT_MAX_TOKENS_CAP`、4096）を廃止し、既定を 512 → 1024 にした。
  モデルに出力専用の上限はなく、真の上限は context window（入力 + 出力）だけなので、サーバーはそこで止める。
  上限を超える `max_completion_tokens` は OpenAI のような 400 にせず、切り詰める
- context window は各モデルの `config.json` から読む（handler の `CONTEXT_WINDOW_KEYS`）。qwen3.6 / 3.8 は
  `text_config.max_position_embeddings` = 262144、Omni は `thinker_config.text_config` の 65536。
  `GET /v1/models` の `context_window` でも返す
- 入力トークン数は prefill 後にしか分からないため、mlx-vlm が各チャンクに付ける `prompt_tokens` を見て生成ループで止める
  （`limit_to_context`）。非 stream も `generate()` をやめて同じ `stream_generate` のループに揃えた
- `finish_reason` は tool call 以外で常に `"stop"` だった。mlx-vlm が最終チャンクで返す `"length"` を反映するよう直した
- YaRN などの context 拡張設定は扱っていない。今のモデルに無く、mlx-vlm 側の対応も未確認のため。
  クライアント切断時に生成を止める処理も今回はやらない判断
- 検証: 単体テスト 303 件、chat の full verify（66 ケース + stream）通過。本番で `/v1/models` の値と、
  `max_completion_tokens: 8` の非 stream / stream がともに `"length"`、自然終了が `"stop"` になることを確認
- 落とし穴: worktree で verify したとき `tests/assets` の link を忘れ、最初の画像ケースで止まった
  （`docs/playbooks/dependency-upgrades.md` に既に手順あり）

## 2026-09-15〜16 — ltx2 に LTX-2.5（`ltx-2.5-distilled`）を追加し、既定にした

- 旧 LTX-2 の `distilled` と並べて追加し、既定だけ切り替えた（ユーザー判断: 比較・切り戻しのため併存）。
  LTX-2.5 専用オプションは `auto_duration` / `enhance_prompt` / `pipeline="dfr"`（T2V のみ）/
  `video_decoder="diffusion"`（2x2 spatial tile 固定）。`distilled` に指定すると 422
- mlx-video の LTX-2.5 port は上流 PR [Blaizzy/mlx-video#52](https://github.com/Blaizzy/mlx-video/pull/52) で
  開発した（経緯・実測は同 PR と `src/kiapi/capabilities/ltx2/README.md`）。マージ前に取り込むため、
  fork の force-push しない branch `kiapi/ltx-2.5` を pin した。PR branch を直接 pin しない理由は、
  rebase や分割で commit が到達不能になりうるため
- pin は `cbb2c10`。PR head `d29c248` に packaging 修正を 1 commit 足した。git / wheel install では
  `mlx_video/models/ltx_2/prompts/*.txt` が入らず、`enhance_prompt` が `FileNotFoundError` で 500 になった
  （editable install の開発中は顕在化しない。旧 pin の Gemma 3 prompt も同じく欠けていた既存不具合）。
  9/16 にユーザー承認のうえ PR branch へも push し、PR head も `cbb2c10` になった（PR 本文・コメントは変更なし）
- `HfSnapshotResource` に `allow_patterns` を追加。LTX-2.5 repo は dev / diffusers の重みも含むため、
  読む 7 ファイル（72.6 GB）だけ取る。cache に一部しかない snapshot も解決されてしまうので、
  status ではワイルドカードでない pattern のファイル存在を個別に確認する
- `PythonPackageResource` は spec が変わっても import できれば ready と判定し、入れ替わらない。
  `verify_attrs` に新 pin にしか無い `LTX25_MODEL_REPO` を足し、旧版を未準備にして activate で入れ替える
- サーバー機の HF cache は、mlx-video 開発時の local dir の `.cache/huggingface/download/*.metadata`
  （commit と etag）から blob を APFS clone、snapshot を symlink で組んだ。再ダウンロードなしで activate が通った
- `mise run verify --kiapi --family ltx2` を full で 13/13 通過（256x256 の小サイズ）。LTX-2.5 の T2V 21.7 秒、
  I2V 20.5 秒、auto_duration + enhance_prompt 39.6 秒、生成音声 17.3 秒、DFR 23.3 秒、diffusion decoder I2V
  26.9 秒、旧 LTX-2 回帰 26.3 秒。mlx の peak は最大 41.19 GB（DFR 以降）で、確保量 44 GB は据え置き。
  1 回目の検証で出た 46.45 GB は、失敗したケースの後の process 累積 peak だった
- 落とし穴: `kiapi deactivate` は確認プロンプトを出すので、非対話で実行すると入力待ちのまま止まる
  （約 3 時間止まった）。package だけ入れ替えるなら `uv pip install --reinstall-package` を使う

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
