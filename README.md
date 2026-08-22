# Flexbone OCR API

A serverless API on **Google Cloud Run** that accepts a JPG image, extracts its
text with **Google Cloud Vision** OCR, and returns the result as JSON.

**Live API:** `https://flexbone-ocr-1035620221514.us-central1.run.app`
**Interactive docs (Swagger UI):** open the base URL in a browser — the root serves live, testable API documentation.

```bash
curl -X POST -F "image=@sample_images/sample_text.jpg" \
  https://flexbone-ocr-1035620221514.us-central1.run.app/extract-text
```

```json
{
  "success": true,
  "text": "Flexbone OCR Challenge\nHello World 2026",
  "confidence": 0.9884,
  "processing_time_ms": 428,
  "message": "Text extracted successfully."
}
```

---

## Testing the live API

Everything below is copy-paste ready against the deployed service. Clone the
repo first so the sample images are available:

```bash
git clone https://github.com/Rafin000/flexbone-ocr-api.git
cd flexbone-ocr-api
API=https://flexbone-ocr-1035620221514.us-central1.run.app
```

**1 — Service is up**
```bash
curl $API/alive
# {"status": "alive"}
```
> The service scales to zero, so the very first request after an idle period
> may take a few seconds to cold start. Subsequent calls are fast.

**2 — Extract text from a JPG** (the core requirement)
```bash
curl -X POST -F "image=@sample_images/sample_text.jpg" $API/extract-text
# text: "Flexbone OCR Challenge\nHello World 2026", confidence: 0.9884
```

**3 — A real document**
```bash
curl -X POST -F "image=@sample_images/receipt.jpg" $API/extract-text
# text: "INVOICE #A-1042\nConsulting\n500.00\n..."  ("cached": false)
```

**4 — Caching**: send the same image again and it returns from cache
```bash
curl -X POST -F "image=@sample_images/receipt.jpg" $API/extract-text
# identical text, "cached": true, processing_time_ms drops to ~1
```

**5 — PNG** (bonus: multi-format)
```bash
curl -X POST -F "image=@sample_images/sample_png.png" $API/extract-text
```

**6 — An image with no text** — succeeds with an empty result rather than erroring
```bash
curl -X POST -F "image=@sample_images/blank.jpg" $API/extract-text
# {"success": true, "text": "", "confidence": 0.0, "message": "No text found in image."}
```

**7 — Batch** (bonus)
```bash
curl -X POST \
  -F "images=@sample_images/sample_text.jpg" \
  -F "images=@sample_images/receipt.jpg" \
  $API/extract-text/batch
```

**8 — Error handling.** Add `-w '\n%{http_code}\n'` to any command to see the
status code.
```bash
echo "not an image" > /tmp/notes.txt
curl -X POST -F "image=@/tmp/notes.txt" $API/extract-text        # 415, unsupported type
curl -X POST $API/extract-text                                    # 400, no file provided
curl -X GET  $API/extract-text                                    # 405, wrong method

dd if=/dev/urandom of=/tmp/big.jpg bs=1m count=12 2>/dev/null
curl -X POST -F "image=@/tmp/big.jpg" $API/extract-text           # 413, over the 10 MB limit
```
Every error returns the same shape: `{"success": false, "error": "..."}`.

**9 — In the browser**: open the base URL for Swagger UI and run any endpoint
interactively, including file upload.

> **Rate limit:** 60 requests per minute per IP. A scripted loop past that
> returns `429` with `{"success": false, "error": "60 per 1 minute"}` — expected,
> not a failure. It resets after a minute.

## API documentation

### `POST /extract-text`
Extract text from an uploaded JPG image.

| | |
|---|---|
| **Method** | `POST` |
| **Content-Type** | `multipart/form-data` |
| **Form field** | `image` (the image file) |
| **Max size** | 10 MB |
| **Formats** | JPG / JPEG / PNG / GIF |

**Request (curl):**
```bash
curl -X POST -F "image=@test_image.jpg" \
  https://flexbone-ocr-1035620221514.us-central1.run.app/extract-text
```

**Success response — `200 OK`:**
```json
{
  "success": true,
  "text": "extracted text content here",
  "confidence": 0.95,
  "processing_time_ms": 1234,
  "message": "Text extracted successfully.",
  "cached": false,
  "metadata": { "width": 900, "height": 300, "format": "JPEG", "mode": "L", "size_kb": 19.44 }
}
```
When the image contains no text, the call still succeeds with `text: ""`,
`confidence: 0.0`, and `message: "No text found in image."`.

### `POST /extract-text/batch`
Batch OCR (bonus) — extract text from **multiple** images in one request.
Upload several files under the `images` field:
```bash
curl -X POST \
  -F "images=@a.jpg" -F "images=@b.jpg" \
  https://flexbone-ocr-1035620221514.us-central1.run.app/extract-text/batch
```
Returns `{ success, count, processing_time_ms, results: [...] }`, where each
result carries its `filename` and either the extracted text or a per-file error
(max 10 files per batch).

**Error response — `4xx / 5xx`:**
```json
{ "success": false, "error": "Unsupported file type 'text/plain'. Allowed: image/gif, image/jpeg, image/jpg, image/png." }
```

**Status codes:**

| Code | Meaning |
|---|---|
| `200` | Text extracted (or no text found) |
| `400` | No file provided / empty file |
| `413` | File exceeds the 10 MB limit |
| `415` | Unsupported file type or extension |
| `502` | OCR provider returned an error |
| `500` | Unexpected server error |

### `GET /alive`
Health/liveness check → `{ "status": "alive" }`.

### `GET /`
Interactive **Swagger UI** — browse and try the API in the browser.
The OpenAPI spec is at `/swagger.json`.

---

## Implementation explanation

**OCR service — a swappable provider abstraction.**
The OCR engine sits behind an `OcrProvider` interface with two implementations —
**Google Cloud Vision** and **Tesseract** — chosen at startup by a factory from
the `OCR_PROVIDER` config (`vision` | `tesseract`). The rest of the app depends
on the interface, not the engine, so swapping providers is a config change, not
a code change. The default is **Vision** (`document_text_detection`), which
returns the full text plus **per-block confidence**, so the API reports a real
confidence score rather than a hard-coded value; Tesseract is the open-source,
no-external-API fallback.

**File upload handling & validation.**
Uploads come in as `multipart/form-data` on the `image` field. Validation is
layered: the content type must be one of the allowed image types, the extension
must match (`.jpg`/`.jpeg`/`.png`/`.gif`) as defence in depth against a spoofed
content type, the file must be non-empty,
and the 10 MB cap is enforced both explicitly and at the framework level
(`MAX_CONTENT_LENGTH`, which makes Flask reject oversized bodies with `413`).

**Deployment strategy.**
The app is containerized (Dockerfile, `python:3.12-slim`) and served by
**gunicorn**. It's deployed to **Cloud Run** straight from source
(`gcloud run deploy --source .`), which uses Cloud Build to build the image,
stores it in Artifact Registry, and runs it serverlessly — scaling to zero when
idle. On Cloud Run the app authenticates to the Vision API through the service
account automatically (no keys in the image). The container binds to the
`$PORT` Cloud Run injects.

**Code structure — app factory + Flask-RESTX namespaces.**
```
config.py                  # Config class — all settings, env-driven
wsgi.py                    # gunicorn / local entry point (app = create_app())
app/
  __init__.py              # create_app() factory: app, logging, limiter, Api, namespaces
  ocr_service.py           # exposes the factory-built OCR provider instance
  providers/               # OCR provider abstraction (interface + factory)
    base.py                # OcrProvider interface + OcrResult
    vision_provider.py     # Google Cloud Vision implementation
    tesseract_provider.py  # Tesseract implementation
    factory.py             # picks the provider from OCR_PROVIDER config
  decorators.py            # @handle_errors, @require_api_key
  responses.py             # consistent JSON envelopes
  extensions.py            # shared Flask-Limiter instance
  cache.py                 # thread-safe LRU cache for identical images
  utils.py                 # text cleanup, image metadata, hashing
  namespaces/
    health.py              # health_ns  -> /alive
    ocr.py                 # ocr_ns     -> /extract-text, /extract-text/batch
sample_images/             # test images (text, receipt, blank, png)
Dockerfile
```
The app is built with an **application factory** (`create_app()`) and routes are
grouped into **Flask-RESTX namespaces** (Resource classes), which also generate
the interactive Swagger UI at the root URL. Concerns are separated so the routes
stay thin, cross-cutting logic lives in decorators, and the OCR provider could be
swapped without touching the web layer.

---

## Run locally

**Prerequisites:** Python 3.12+ (or Docker), and Google credentials with the
Vision API enabled.

### With Docker (matches production)
```bash
# Build
docker build -t flexbone-ocr .

# Run, mounting your gcloud credentials for local Vision access.
# The container runs as the non-root user "appuser", so mount into its home.
docker run -p 8080:8080 \
  -v "$HOME/.config/gcloud:/home/appuser/.config/gcloud:ro" \
  -e GOOGLE_CLOUD_PROJECT=<your-project-id> \
  flexbone-ocr
```

### Without Docker
```bash
pip install -r requirements.txt
gcloud auth application-default login
gcloud auth application-default set-quota-project <your-project-id>
python wsgi.py     # http://localhost:8080
```

> Note: with local **user** credentials, set the ADC quota project (above). On
> Cloud Run this is automatic via the service account.

### Test it
```bash
curl -X POST -F "image=@sample_images/sample_text.jpg" http://localhost:8080/extract-text
curl -X POST -F "image=@sample_images/blank.jpg"       http://localhost:8080/extract-text   # no-text case
curl http://localhost:8080/alive
```

---

## Bonus features implemented

| Feature | How |
|---|---|
| **Confidence scores** | Averaged from Cloud Vision's per-block confidence |
| **Multiple formats (PNG, GIF)** | JPG + PNG + GIF accepted (still rejects everything else) |
| **Text preprocessing** | Trailing whitespace trimmed, blank-line runs collapsed |
| **Image metadata extraction** | Width, height, format, mode, size (via Pillow) |
| **Caching for identical images** | SHA-256 of the bytes keys an in-memory LRU cache; repeats return `cached: true` instantly |
| **Rate limiting** | Per-client-IP limit (default 60/min) via Flask-Limiter → `429` when exceeded |
| **Batch processing** | `POST /extract-text/batch` handles many images per call |

> The cache and rate-limiter are in-memory (per instance) — perfect for this
> service; a shared store (e.g. Redis) would be the next step for multi-instance
> consistency.

## Configuration

All via environment variables (see `config.py`):

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8080` | Port to bind (Cloud Run sets this) |
| `OCR_PROVIDER` | `vision` | OCR engine: `vision` or `tesseract` |
| `MAX_FILE_SIZE_MB` | `10` | Upload size limit |
| `API_KEY` | _(empty)_ | If set, requires this key in the `Authorization` header |
| `RATE_LIMIT` | `60 per minute` | Per-IP rate limit |
| `RATE_LIMIT_ENABLED` | `true` | Toggle rate limiting |
| `CACHE_ENABLED` | `true` | Toggle identical-image caching |
| `CACHE_MAX_ENTRIES` | `128` | LRU cache size |
| `MAX_BATCH_FILES` | `10` | Max images per batch request |
| `GOOGLE_CLOUD_PROJECT` | _(env)_ | GCP project id |

---

## Deploy to Cloud Run
```bash
gcloud run deploy flexbone-ocr \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi
```

## Tech stack
Python · Flask · Flask-RESTX (Swagger) · Flask-Limiter · Pillow · gunicorn ·
Google Cloud Vision · Docker · Google Cloud Run
