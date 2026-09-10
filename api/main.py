"""Public API for the drumsep web frontend.

Endpoints:
  GET  /v1/health                    liveness check
  POST /v1/uploads                   get a signed URL to PUT the raw audio directly to GCS
  POST /v1/process                   run ffmpeg + demucs on an uploaded file, return signed
                                      download URLs (24h) for the resulting stems

Only requests whose `Origin` header matches ALLOWED_ORIGIN are served (see
OriginCheckMiddleware below). This is meant to keep the API restricted to
the GitHub Pages frontend, not as a substitute for real authentication --
see README for the tradeoffs of that decision.
"""
import logging
import os
import re
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from gcs_utils import BUCKET_NAME, blob_exists, generate_download_url, generate_upload_url
from processing import ProcessingError, process_track

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

ALLOWED_ORIGIN = os.environ["ALLOWED_ORIGIN"].rstrip("/")

ALLOWED_CONTENT_TYPES = {
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/flac": ".flac",
    "audio/ogg": ".ogg",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
}
SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")

app = FastAPI(title="drumsep-api")

# Browser-side enforcement: only fetch()/XHR calls made from the GitHub
# Pages origin are allowed to read the response.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    max_age=3600,
)


@app.middleware("http")
async def enforce_allowed_origin(request: Request, call_next):
    """Server-side enforcement: reject state-changing calls whose Origin
    header doesn't match, regardless of whether the client honors CORS
    (CORS only stops *browsers* from exposing the response to JS running
    on another origin -- it does not stop a direct curl/script call).

    NOTE: an Origin header is trivially spoofable by non-browser clients,
    so this is a cheap allow-list, not real auth. See README "Tradeoffs".
    """
    if request.method == "OPTIONS" or request.url.path == "/v1/health":
        return await call_next(request)

    origin = request.headers.get("origin", "")
    if origin.rstrip("/") != ALLOWED_ORIGIN:
        return JSONResponse(status_code=403, content={"detail": "origin not allowed"})
    return await call_next(request)


class UploadRequest(BaseModel):
    filename: str
    content_type: str


class UploadResponse(BaseModel):
    track_id: str
    object_name: str
    upload_url: str
    expires_in_minutes: int = 15


class ProcessRequest(BaseModel):
    track_id: str
    object_name: str


class Stem(BaseModel):
    name: str
    download_url: str


class ProcessResponse(BaseModel):
    track_id: str
    stems: list[Stem]
    expires_in_hours: int = 24


@app.get("/v1/health")
def health():
    return {"status": "ok"}


@app.post("/v1/uploads", response_model=UploadResponse)
def create_upload_url(req: UploadRequest):
    if req.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported content_type '{req.content_type}'. "
            f"Allowed: {sorted(ALLOWED_CONTENT_TYPES)}",
        )

    track_id = str(uuid.uuid4())
    safe_name = SAFE_NAME_RE.sub("_", os.path.basename(req.filename)) or "input"
    object_name = f"uploads/{track_id}/{safe_name}"

    upload_url = generate_upload_url(object_name, req.content_type)
    return UploadResponse(track_id=track_id, object_name=object_name, upload_url=upload_url)


@app.post("/v1/process", response_model=ProcessResponse)
def process(req: ProcessRequest):
    # Basic sanity check: the object must live under the track's own upload
    # prefix, so one client can't ask us to process someone else's file.
    if not req.object_name.startswith(f"uploads/{req.track_id}/"):
        raise HTTPException(status_code=400, detail="object_name does not match track_id")

    if not blob_exists(req.object_name):
        raise HTTPException(status_code=404, detail="uploaded object not found")

    try:
        stem_objects = process_track(req.track_id, req.object_name, BUCKET_NAME)
    except ProcessingError as exc:
        logger.exception("processing failed for track %s", req.track_id)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    stems = [
        Stem(name=os.path.basename(obj), download_url=generate_download_url(obj))
        for obj in stem_objects
    ]
    return ProcessResponse(track_id=req.track_id, stems=stems)
