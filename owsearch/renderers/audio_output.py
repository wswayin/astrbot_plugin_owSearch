from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from .image_output import ImageFile, save_media_bytes
from ..utils.time import now_compact


class AudioConversionError(RuntimeError):
    pass


def _resolve_ffmpeg_executable() -> str:
    configured = os.environ.get("OWSEARCH_FFMPEG_PATH", "").strip()
    if configured:
        path = Path(configured)
        if path.exists():
            return str(path)

    discovered = shutil.which("ffmpeg")
    if discovered:
        return discovered

    try:
        import imageio_ffmpeg
    except Exception as exc:  # pragma: no cover - depends on runtime package state.
        raise AudioConversionError("未找到 ffmpeg，且 imageio-ffmpeg 不可用。") from exc

    try:
        return str(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception as exc:  # pragma: no cover - depends on runtime package state.
        raise AudioConversionError(f"imageio-ffmpeg 无法提供 ffmpeg：{exc}") from exc


def convert_audio_file_to_wav(
    input_path: Path,
    output_dir: Path,
    *,
    prefix: str,
    sample_rate: int = 16000,
    timeout_seconds: int = 45,
) -> ImageFile:
    output_dir.mkdir(parents=True, exist_ok=True)
    if not input_path.exists():
        raise AudioConversionError(f"音频源文件不存在：{input_path}")

    stem = f"{prefix}_{now_compact()}_{uuid4().hex[:8]}"
    output_path = output_dir / f"{stem}.wav"
    ffmpeg = _resolve_ffmpeg_executable()
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(int(sample_rate or 16000)),
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=max(5, int(timeout_seconds or 45)),
        )
    except subprocess.TimeoutExpired as exc:
        raise AudioConversionError("音频转码超时。") from exc
    except OSError as exc:
        raise AudioConversionError(f"无法启动 ffmpeg：{exc}") from exc

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        if len(detail) > 360:
            detail = detail[-360:]
        raise AudioConversionError(f"ffmpeg 转码失败：{detail or completed.returncode}")
    if not output_path.exists() or output_path.stat().st_size <= 44:
        raise AudioConversionError("ffmpeg 未生成有效 wav 文件。")
    return ImageFile(path=output_path, media_type="audio/wav")


def convert_audio_bytes_to_wav(
    data: bytes,
    output_dir: Path,
    *,
    prefix: str,
    media_type: str,
    sample_rate: int = 16000,
    keep_source: bool = False,
) -> ImageFile:
    source = save_media_bytes(data, output_dir, prefix=f"{prefix}_source", media_type=media_type)
    try:
        return convert_audio_file_to_wav(
            source.path,
            output_dir,
            prefix=prefix,
            sample_rate=sample_rate,
        )
    finally:
        if not keep_source:
            try:
                source.path.unlink()
            except OSError:
                pass
