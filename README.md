# Flexbone OCR API

A serverless API on **Google Cloud Run** that accepts a JPG image, extracts its
text with **Google Cloud Vision** OCR, and returns the result as JSON.

**Live API:** `https://flexbone-ocr-1035620221514.us-central1.run.app`

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

## API documentation

### `POST /extract-text`
Extract text from an uploaded JPG image.

| | |
|---|---|
| **Method** | `POST` |
| **Content-Type** | `multipart/form-data` |
| **Form field** | `image` (the JPG file) |
| **Max size** | 10 MB |
| **Formats** | JPG / JPEG |

**Request (curl):**
```bash
curl -X POST -F "image=@test_image.jpg" <base-url>/extract-text
```

**Success response — `200 OK`:**
```json
{
  "success": true,
  "text": "extracted text content here",
  "confidence": 0.95,
  "processing_time_ms": 1234,
  "message": "Text extracted successfully."
}
```
When the image contains no text, the call still succeeds with `text: ""`,
`confidence: 0.0`, and `message: "No text found in image."`.

**Error response — `4xx / 5xx`:**
```json
{ "success": false, "error": "Unsupported file type 'text/plain'. Allowed: image/jpeg, image/jpg." }
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
Landing page with usage info.

---

## Implementation explanation

**OCR service — Google Cloud Vision.**
I used Cloud Vision's `document_text_detection`, which returns the full text
plus **per-block confidence**, so the API can report a real confidence score
(averaged across text blocks) rather than a hard-coded value. Vision was chosen
over Tesseract because it integrates natively with GCP, gives higher accuracy on
varied image quality, and needs no OCR engine bundled into the container.

**File upload handling & validation.**
Uploads come in as `multipart/form-data` on the `image` field. Validation is
layered: the content type must be `image/jpeg`, the extension must be `.jpg`/`.jpeg`
(defence in depth against a spoofed content type), the file must be non-empty,
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

**Code structure.**
```
config.py            # Config class — all settings, env-driven
wsgi.py              # gunicorn / local entry point
app/
  __init__.py        # Flask app + config loading
  views.py           # routes: /, /alive, /extract-text  (thin)
  ocr_service.py     # Cloud Vision wrapper (swappable)
  decorators.py      # @handle_errors, @require_api_key
  responses.py       # consistent JSON envelope
sample_images/       # test images (text, receipt, blank)
Dockerfile
```
Concerns are separated so the routes stay thin, cross-cutting logic lives in
decorators, and the OCR provider could be swapped without touching the web layer.

---

## Run locally

**Prerequisites:** Python 3.12+ (or Docker), and Google credentials with the
Vision API enabled.

### With Docker (matches production)
```bash
# Build
docker build -t flexbone-ocr .

# Run, mounting your gcloud credentials for local Vision access
docker run -p 8080:8080 \
  -v "$HOME/.config/gcloud:/root/.config/gcloud:ro" \
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

## Configuration

All via environment variables (see `config.py`):

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8080` | Port to bind (Cloud Run sets this) |
| `MAX_FILE_SIZE_MB` | `10` | Upload size limit |
| `ALLOW_PNG` | `false` | Also accept PNG (bonus) |
| `API_KEY` | _(empty)_ | If set, requires this key in the `Authorization` header |
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
Python · Flask · gunicorn · Google Cloud Vision · Docker · Google Cloud Run
