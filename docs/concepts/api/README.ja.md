# API

[English](README.md) | **日本語**

この concept は public endpoint vocabulary、capability discovery、OpenAPI
documentation layer を説明します。

## Endpoint Organization

chat と embedding は標準 modality endpoint を公開します。

- `POST /v1/chat/completions`
- `POST /v1/embedding`

generation endpoint は次の形式です。

```text
POST /v1/<domain>/<family>/<operation>
```

- `domain` は image、audio、video などの modality で capability をまとめます。
- `family` は canonical lowercase capability identifier で、source directory と一致します。
- `operation` はその family がサポートする vocabulary です。

endpoint は operation vocabulary を表します。`model` parameter は、その vocabulary
全体をサポートする交換可能な variant を選びます。job、file、error、authentication、
memory management などの横断要素は共有し、family の request payload は固有のまま
保ちます。

## Model Discovery

`GET /v1/models` は OpenAI-compatible を維持し、chat model を一覧します。それ以外は
`/v1/embedding/models` または `/v1/{domain}/{family}/models` から発見します。

model name は family 内の variant を識別し、family name を繰り返しません。

## OpenAPI Layers

kiapi は 2 層の machine-readable documentation を公開します。

1. `GET /openapi.json` は共通 endpoint、capability、documentation URL を一覧します。
2. `GET /v1/{domain}/{family}/openapi.json` は選択した capability の operation、
   schema、example、guidance を説明します。

root document は「この server で何ができ、次にどこを見ればよいか」に答えます。
capability document は「この operation をどう呼ぶか」に答えます。

`CapabilitySpec.summary` は簡潔で task-oriented な discovery description とします。
`CapabilitySpec.description` は詳細な Markdown guidance を持ちます。operation 固有の
詳細は endpoint docstring と Pydantic schema が所有します。

## Related Concepts

- [Application](../application/README.ja.md)
- [Jobs and Files](../jobs-and-files/README.ja.md)
- [Architecture overview](../../../ARCHITECTURE.ja.md)
