from typing import Optional


def format_duration(seconds):
    if not seconds:
        return None
    # Handle both int and formatted string like "0:08"
    if isinstance(seconds, str):
        parts = seconds.split(':')
        if len(parts) == 2:
            m, s = parts
            total = int(m) * 60 + int(s)
        elif len(parts) == 3:
            h, m, s = parts
            total = int(h) * 3600 + int(m) * 60 + int(s)
        else:
            return None
    else:
        total = int(seconds)
    h, m = divmod(total, 3600)
    m, s = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def format_bitrate(bitrate: Optional[str]) -> Optional[str]:
    if not bitrate:
        return None
    try:
        return f"{int(bitrate) / 1000:.0f} kbps"
    except:
        return None


def format_fps(fps_str: Optional[str]) -> Optional[str]:
    if not fps_str:
        return None
    try:
        if '/' in fps_str:
            n, d = fps_str.split('/')
            return f"{float(n) / float(d):.2f}"
        return fps_str
    except:
        return None


def format_filesize(size: int) -> str:
    s = float(size)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if s < 1024:
            return f"{s:.1f} {unit}"
        s /= 1024
    return f"{s:.1f} TB"