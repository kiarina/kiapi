# API

**English** | [日本語](README.ja.md)

This concept describes the public endpoint vocabulary, capability discovery,
and OpenAPI documentation layers.

## Endpoint Organization

Chat and embedding expose standard modality endpoints:

- `POST /v1/chat/completions`
- `POST /v1/embedding`

Generation endpoints follow:

```text
POST /v1/<domain>/<family>/<operation>
```

- `domain` groups capabilities by modality, such as image, audio, or video.
- `family` is the canonical lowercase capability identifier and matches its
  source directory.
- `operation` is the vocabulary supported by that family.

An endpoint represents an operation vocabulary. The `model` parameter selects a
replaceable variant that supports the whole vocabulary. Cross-cutting concerns
such as jobs, files, errors, authentication, and memory management remain
shared, while family request payloads remain specific.

## Model Discovery

`GET /v1/models` remains OpenAI-compatible and lists chat models. Other models
are discovered through `/v1/embedding/models` or
`/v1/{domain}/{family}/models`.

Model names identify variants within a family and do not repeat the family
name.

## OpenAPI Layers

kiapi exposes two machine-readable documentation layers:

1. `GET /openapi.json` lists common endpoints, capabilities, and documentation
   URLs.
2. `GET /v1/{domain}/{family}/openapi.json` describes the selected capability's
   operations, schemas, examples, and guidance.

The root document answers “what can this server do, and where should I look
next?” A capability document answers “how do I call this operation?”

`CapabilitySpec.summary` is a concise, task-oriented discovery description.
`CapabilitySpec.description` contains detailed Markdown guidance. Endpoint
docstrings and Pydantic schemas own operation-specific details.

## Related Concepts

- [Application](../application/)
- [Jobs and Files](../jobs-and-files/)
- [Architecture overview](../../../ARCHITECTURE.md)
