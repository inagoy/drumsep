"""Audio pipeline: download -> normalize with ffmpeg -> drum-stem separation
with demucs (drumsep model) -> upload stems.

This generalizes dockerapp/GCP-job/process_audio.py (which scanned a whole
bucket for pre-named `*drums.{mp3,wav}` files coming from an earlier
spleeter step) into a function that processes exactly one user-uploaded
file, identified by `track_id`. It also adds an explicit ffmpeg
normalization pass so we accept any container/codec ffmpeg can decode
(m4a, aac, webm/opus, etc.), not just the mp3/wav/flac/ogg the drumsep
script hardcodes.
"""
import glob
import logging
import os
import shutil
import subprocess
import tempfile

from gcs_utils import download_to_file, upload_from_file

logger = logging.getLogger("processing")

DEMUCS_MODEL_REPO = os.environ.get("DEMUCS_MODEL_REPO", "/drumsep/model")
DEMUCS_MODEL_NAME = os.environ.get("DEMUCS_MODEL_NAME", "49469ca8")
STEMS_PREFIX = "stems"
MAX_INPUT_BYTES = int(os.environ.get("MAX_INPUT_BYTES", 200 * 1024 * 1024))  # 200MB


class ProcessingError(Exception):
    pass


def _run(cmd, **kwargs):
    logger.info("running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        logger.error("command failed (%s): %s", result.returncode, result.stderr[-4000:])
        raise ProcessingError(f"{cmd[0]} failed: {result.stderr[-2000:]}")
    return result


def _normalize_with_ffmpeg(input_path: str, workdir: str) -> str:
    """Transcode arbitrary input audio into a clean PCM wav.

    This isolates demucs/torchaudio from container/codec quirks in
    whatever the user uploaded, and gives us one predictable format to
    feed the model.
    """
    normalized_path = os.path.join(workdir, "normalized.wav")
    _run(
        [
            "ffmpeg", "-y",
            "-i", input_path,
            "-ac", "2",
            "-ar", "44100",
            "-sample_fmt", "s16",
            normalized_path,
        ]
    )
    return normalized_path


def _separate_drums(normalized_path: str, workdir: str) -> str:
    output_dir = os.path.join(workdir, "output")
    os.makedirs(output_dir, exist_ok=True)
    _run(
        [
            "demucs",
            "--repo", DEMUCS_MODEL_REPO,
            "-o", output_dir,
            "-n", DEMUCS_MODEL_NAME,
            normalized_path,
        ]
    )
    stems_dir = os.path.join(output_dir, DEMUCS_MODEL_NAME, "drums")
    stem_files = glob.glob(os.path.join(stems_dir, "*"))
    if not stem_files:
        raise ProcessingError(f"demucs produced no output in {stems_dir}")
    return stems_dir


def process_track(track_id: str, input_object: str, bucket_name: str) -> list[str]:
    """Downloads `input_object`, separates it into drum stems, uploads the
    results under `stems/{track_id}/`, and returns the list of uploaded
    object names.
    """
    workdir = tempfile.mkdtemp(prefix=f"track-{track_id}-")
    try:
        local_input = os.path.join(workdir, "input" + os.path.splitext(input_object)[1])
        download_to_file(input_object, local_input)

        size = os.path.getsize(local_input)
        if size > MAX_INPUT_BYTES:
            raise ProcessingError(
                f"input is {size} bytes, exceeds MAX_INPUT_BYTES={MAX_INPUT_BYTES}"
            )

        normalized_path = _normalize_with_ffmpeg(local_input, workdir)
        stems_dir = _separate_drums(normalized_path, workdir)

        uploaded = []
        for stem_path in sorted(glob.glob(os.path.join(stems_dir, "*"))):
            stem_name = os.path.basename(stem_path)
            object_name = f"{STEMS_PREFIX}/{track_id}/{stem_name}"
            upload_from_file(object_name, stem_path)
            uploaded.append(object_name)

        return uploaded
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
