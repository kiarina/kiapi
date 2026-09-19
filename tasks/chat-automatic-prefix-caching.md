# chat に Automatic Prefix Caching を導入する

## 目的

chat request ごとに再計算している共通 prompt prefix の KV cache を再利用し、長い system message、
tool schema、conversation history を繰り返し送るときの time to first token（TTFT）を短縮する。

対象は生成結果の response cache ではない。次のような、先頭から連続して一致する token prefix の
prefill 結果を再利用する。

```text
system message
tools schema
conversation history
current user message
```

## 現状（確認: 2026-09-19）

- kiapi は chat request ごとに `apply_chat_template` から prompt 全体を作り、毎回すべてを
  `stream_generate` へ渡している
- chat model 自体は resident だが、request 間で KV cache は保持していない
- `qwen3_5.py` と `qwen3_omni.py` は `prompt_cache_state` / `apc_manager` を渡していない
- mlx-vlm には次の二つの再利用機構がある
  - `PromptCacheState`: 一つの会話を呼び出し側が明示的に保持する方式
  - `APCManager`: token prefix を hash で照合する Automatic Prefix Caching（APC）。request 横断、
    block 単位、memory / disk tier、LRU、統計、tenant salt を持つ
- kiapi の OpenAI-compatible API は stateless で、client は毎回全 history を送る。API に conversation IDを
  追加せず利用できる `APCManager` を第一候補とする
- `pyproject.toml` / `uv.lock` は mlx-vlm 0.7.1。開発機の `.venv` は調査時に 0.6.3 のままだったため、
  実装・API確認・計測はサーバー機で `git pull --ff-only` と `make update` 後の 0.7.1 を正典にする
- mlx-vlm upstream の APC は更新が速い。着手時に 0.7.1 の実APIとmainとの差分を確認し、mainにしかない
  APIを前提に実装しない。必要なら依存更新を独立した判断として扱う

参考:

- mlx-vlm README の `Automatic Prefix Caching (APC)`
- mlx-vlm `mlx_vlm/apc.py`
- mlx-vlm `stream_generate` の `apc_manager` / `apc_tenant` / `cached_tokens`
- mlx-lm `examples/chat.py` と `models/cache.py`（prompt cacheの基礎実装）

## 前提と設計上の注意

### cache hit の単位

意味的に同じ JSON ではなく、chat template 適用後の token 列が先頭から一致する必要がある。
tool の順序、schema の key 順、description、空白、`enable_thinking` などが変われば、その token 以降は
miss する。system / tools / history を独立した cache として任意合成するのではなく、APC に最長一致prefixを
選ばせる。

### lifecycle と memory budget

APC manager は model / tokenizer / chat template / cache layout ごとに分離する。同名modelのpayloadに
紐づけるのが第一候補。model eviction / release 後に、そのmodelのmemory cacheだけが残らないようにする。

kiapi のmemory managerは現在model weightとpeak headroomを管理している。APCのresident bytesを無視して
Metal / unified memoryを圧迫しないこと。少なくとも以下を満たす。

- APCのmemory上限を設定できる
- 既定値は保守的にするか、初回導入では明示的opt-inにする
- model acquire / evictionとの責務を文書化する
- cache evictionとmodel evictionの順序を決める
- server再起動で消えるmemory tierと、残るdisk tierを区別する

### security / isolation

このkiapiはtailnet内の個人利用だが、prefixにはsystem prompt、tool schema、会話内容が入る。
diskへ永続化する場合は既定path、permission、容量上限、削除方法を明示する。将来複数利用者を扱っても
workspace間でcacheを共有しないよう、`apc_tenant`相当の分離境界を用意する。request headerをそのまま
信用する設計にするか、server設定で固定するかを決める。

### multimodal

画像・音声・動画はtoken列だけで同一性を判断できない。media内容のhashと、vision / audio feature、
Omni固有cache layoutを考慮する必要がある。mlx-vlm APCにはmedia hashとcustom cache snapshotの経路が
あるが、kiapiのQwen3-Omniにはdeepstack patch C/Hもある。

最初の実装は `qwen3.6-27b` / `qwen3.8-27b` のtext-onlyに限定し、Omniとmediaを同時に有効化しない。
Omni text-only、image、audio、video、image+videoはそれぞれ独立してcold/warm parityを確認してから広げる。

### response semantics

- 改善対象は主にTTFT / prefill時間。生成開始後のgeneration tokens/secは原則変わらない
- responseの`usage.prompt_tokens`は、再計算したtoken数ではなく論理上のprompt全体を維持する
- cache hit token数は`usage`を書き換えず、別の観測値として扱う
- coldとwarmでattention kernelのshapeが変わり、浮動小数点の演算順により同じseedでもbit-identicalに
  ならない可能性がある。cacheしたKV自体を近似する機能ではない
- tool-call用assistant prefill（`<tool_call>...`）と推論時のprompt prefill/cacheを混同しない

## 実装方針

### 1. まず実測可能にする

- GPU検証scriptに、同じ長いprefixを2回以上送るbenchmark caseを追加する
- 各runについて最低限次を記録する
  - model / modality / prompt tokens / cached tokens
  - cold / warm TTFT
  - prefill tokens/sec（取得可能なら）
  - generation tokens/sec
  - peak memoryとAPC resident bytes
  - hit / missとmiss理由を追えるlogまたはstats
- `cached_tokens`はmlx-vlmのterminal chunkから失わずにkiapiの観測へ渡す
- public responseへ独自fieldを追加するか、log / health / cache endpointに置くかを実装前に決める。
  OpenAI互換responseを不用意に変えない

### 2. text-only memory APC

- model payloadごとにAPC managerを生成・保持する
- `qwen3_5.run()` の `stream_generate`へ渡す
- non-stream / streamが同じcache経路を通ることを確認する
- prefixが完全一致、途中で分岐、toolsだけ変更、system変更、history追加、全missを単体テストする
- cache managerそのもののGPU tensor処理はCPU unit testでmockし、実KVの正しさはverify scriptで確認する
- memory上限、block size、enabled、tenant/isolationをkiapi settingsへ追加し、full templateとREADME/OpenAPIへ反映する

### 3. lifecycle / administration

- model release時にAPC memoryをreleaseできるようにする
- APCを止めても通常生成へ確実にfallbackする
- statsを確認できる手段を追加する。候補:
  - `/health`に要約
  - chat固有cache stats endpoint
  - CLI/status
- cache resetを用意する場合、全model / model指定 / memory only / diskを区別する
- resetは生成中のleased cacheを壊さず、single-flight worker上で直列化する

### 4. disk tier

- memory APCの効果とmemory costを実測してから追加する
- default pathはkiapiのcache directory配下に置き、mlx-vlmのglobal defaultへ暗黙に混在させない
- 容量上限とLRU、server再起動後のwarm-disk hit、破損時fallback、model/version変更時のnamespace分離を検証する
- source promptやtoken列など、復元に不要な平文をmetadataへ保存しない

### 5. Omni / multimodal

次の順に一つずつ有効化し、各段階でcold/warm parityとserverの生存を確認する。

1. `qwen3-omni` text-only
2. image
3. audio
4. video（短いもの、2048 tokenを越えるもの）
5. image + video（patch C）
6. 2048 tokenを越えるvisual prompt（patch H / chunked prefill）

mediaがprefixに含まれる場合と、mediaが差分suffix側にある場合を分ける。同じpathで内容が変わった場合、
異なるpathで内容が同じ場合、videoの`fps` / `use_audio_in_video`が変わった場合に誤hitしないことを確認する。

## 計測条件

サーバー機（Mac Studio M4 Max 128GB）で、他requestがなく`queue_len=0`の状態で測る。model warmup時間と
prompt cache効果を混ぜないため、model load済みのcold-cacheを基準にする。

最低限のmatrix:

| model | prefix | suffix | 期待 |
|---|---:|---:|---|
| qwen3.8-27b | systemのみ（短） | user | hitするが効果小 |
| qwen3.8-27b | system + 長いtools | user | toolsまでhit |
| qwen3.8-27b | 10k程度のhistory | 新しいuser turn | historyまでhit、TTFT短縮 |
| qwen3.8-27b | toolsの末尾だけ変更 | user | 変更前までpartial hit |
| qwen3.8-27b | system変更 | 同じhistory | 早い位置でmiss |
| qwen3-omni | text-only長history | user | Omni対応後にhit |
| qwen3-omni | 長いvideo prefix | text suffix | multimodal対応後に安全にhit |

各caseはcold 1回、同一条件warmを最低3回測り、中央値を残す。最低限、TTFT、cached tokens、peak memory、
response/tool_calls、finish_reasonを記録する。成果は機種名・設定・mlx-vlm version・commitとともに
`HISTORY.md`へ記録する。

## 完了条件

- OpenAI-compatible requestを変えず、全historyを再送するclientが自動でprefix cacheの恩恵を受ける
- qwen3.6 / qwen3.8 text-onlyでsystem / tools / historyのpartial hitを確認できる
- hit時に`cached_tokens > 0`となり、10k程度のhistoryのwarm TTFTがcoldより明確に短い
- miss時とAPC無効時のresponse semanticsが従来と同じ
- stream / non-stream、tool choice（auto / required / specific）、parallel tool callsが回帰しない
- cache memoryが設定上限内に収まり、model eviction / server restart / cache resetでleakやstale参照がない
- `usage.prompt_tokens`、finish reason、context-window制限がcache hit時にも正しい
- `make`とchatのCPU unit testが成功する
- サーバー機で`mise run verify --kiapi --family chat`をfullで通す
- Omni / multimodalを未対応で完了させる場合は、設定上明示的に対象外にし、このtaskを閉じず残件を
  独立taskへ分割する

## 最初の一手

1. サーバー機でこのrepositoryを同期し、`make update`後に`.venv`のmlx-vlmが0.7.1であることを確認する
2. 0.7.1の`stream_generate`、`APCManager`、model cache layout対応を実コードで確認する
3. code変更前に、現状のcold TTFTを上のtext-only matrixで測る
4. qwen3.8 payloadにmemory-only APCを最小構成で差し込み、同一prompt 2回目の`cached_tokens`とTTFTを測る
5. 効果とmemory増加を確認してからsettings / lifecycle / testsへ広げる
