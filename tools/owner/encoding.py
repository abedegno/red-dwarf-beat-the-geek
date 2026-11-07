"""Conservative PAL H.264/AAC settings; profiles never alter game timing."""

from dataclasses import asdict, dataclass, replace
import hashlib
import json
import re


@dataclass(frozen=True)
class EncodingProfile:
    name: str
    crf: int
    preset: str
    audio_bitrate: str
    width: int = 768
    height: int = 576
    fps: int = 25
    threads: int = 2

    def identity(self):
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True).encode()
        ).hexdigest()


def profile(name, overrides=None):
    profiles = {
        "fidelity": EncodingProfile("fidelity", 18, "fast", "160k"),
        "web": EncodingProfile("web", 22, "medium", "96k"),
    }
    if name not in profiles:
        raise ValueError("Unknown encoding profile: " + name)
    try:
        p = replace(profiles[name], **(overrides or {}))
    except TypeError as error:
        raise ValueError("Unknown encoding override") from error
    if (
        not isinstance(p.crf, int)
        or not 16 <= p.crf <= 28
        or p.preset not in ["fast", "medium", "slow"]
        or not re.fullmatch(r"(?:64|80|96|112|128|160|192)k", p.audio_bitrate)
        or not isinstance(p.threads, int)
        or not 1 <= p.threads <= 16
        or (p.width, p.height, p.fps) != (768, 576, 25)
    ):
        raise ValueError(
            "Invalid encoding settings; preserve 768x576 PAL 25fps, CRF16–28 and supported AAC bitrate/preset"
        )
    return p
