# depthpro

**English** | [日本語](README.ja.md)

[mflux Depth Pro](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/depth_pro/README.md) estimates a depth map from a single image and produces the following:

- Depth map in grayscale PNG
- optionally compressed NPZ with raw depth array and min/max

## API

| Endpoint | Name | Description |
|---|---|---|
| `POST /v1/image/depthpro/estimate` | Depth estimation | Estimate depth map from Files API images. |
| `GET /v1/image/depthpro/models` | Model list | Returns a list of available models. |
| `GET /v1/image/depthpro/openapi.json` | OpenAPI | Returns detailed input/output specifications, usage, and TIPS. |

## API Docs

- [OpenAPI JSON](https://kiarina.github.io/kiapi/v1/image/depthpro/openapi.json)
- [Swagger UI](https://kiarina.github.io/kiapi/v1/image/depthpro/docs.html)
- [ReDoc](https://kiarina.github.io/kiapi/v1/image/depthpro/redoc.html)

## Dependencies

| Package | License | Description |
|---|---|---|
| [mflux](https://github.com/filipstrand/mflux) | MIT | Uses Depth Pro's MLX implementation. |

## Models

| Model | License | Terms | Size | Description |
|---|---|---|---:|---|
| [apple/DepthPro](https://huggingface.co/apple/DepthPro) | Apple Depth Pro License | Not required | 1.8 GB | `base` (default). Estimating relative depth from a single image. Default is `quantize: 8`. A model may be downloaded the first time you use it. |

## Notes

- **Response format**:
  `include_depth_data: true` (default) creates two artifacts, PNG and NPZ.
  sync also returns Job JSON. `include_depth_data: false` means only PNG,
  sync returns raw PNG bytes by default. If you need Job JSON
  Add `Accept: application/json`.
- **quantize override**:
  `quantize` is `3` / `4` / `5` / `6` / `8` / `null`. Usually a resident model is used, but
  If you specify `quantize` in the request that is different from the default value, it will be used as a one-time temporary model.
  Load, execute, release.
- **Input size limit**:
  By default, the input image is up to `4096 * 4096` pixels. Depth Pro resizes internally, but
  Limits inputs that are too large to occupy the queue for too long.
- **Progress**:
  Depth Pro has a single forward pass and no detailed step notification, so it uses time-based
  Stream synthetic progress.

## Quickstart

### estimate — Depth estimation

Upload the source image first:
```bash
IMG=$(curl -sS -X POST http://localhost:${PORT:-8000}/v1/files \
-F "file=@source.png" | jq -r .file_id)
```
Create both depth PNG and raw data NPZ:
```bash
PARAMS=$(jq -n \
--arg img "$IMG" \
'{
  model: "base",
  mode: "sync",
  image: {type: "file_id", file_id: $img},
  quantize: 8,
  include_depth_data: true
}')

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/depthpro/estimate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" | jq .
```
If you just want the depth PNG for display:
```bash
PARAMS=$(jq -n \
--arg img "$IMG" \
'{
  model: "base",
  mode: "sync",
  image: {type: "file_id", file_id: $img},
  include_depth_data: false
}')

curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/depthpro/estimate \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" \
-o depth.png
```

### async

```bash
PARAMS=$(jq -n \
--arg img "$IMG" \
'{
  model: "base",
  mode: "async",
  image: {type: "file_id", file_id: $img},
  include_depth_data: true
}')

JOB=$(
curl -sS -X POST http://localhost:${PORT:-8000}/v1/image/depthpro/estimate \
-H 'Accept: application/json' \
-H 'Content-Type: application/json' \
--data-binary "$PARAMS" |
jq -r .job_id
)

curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq .
```
After completion, the Job's `artifacts` or `result.depth_image_file_id` /
You can retrieve artifacts using `result.depth_data_file_id`.
```bash
FID=$(curl -sS http://localhost:${PORT:-8000}/v1/jobs/$JOB | jq -r .result.depth_image_file_id)
curl -sS http://localhost:${PORT:-8000}/v1/files/$FID/download -o depth.png
```
