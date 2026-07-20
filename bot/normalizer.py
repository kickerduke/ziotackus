import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

_URL_RE = re.compile(r'https?://[^\s<>"\']{4,}')
_TRAILING_PUNCT = re.compile(r'[.,)\]>\'\"]+$')

_TRACKING_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "utm_referrer",
    "fbclid", "gclid", "dclid", "igshid", "igsh",
    "_ga", "_gl",
    "mc_cid", "mc_eid",
    "ref", "source", "via",
})

_ALLOWED_DOMAINS = frozenset({
    "9gag.com", "brickset.com", "fb.watch", "fb.me", "fumettologica.it",
    "ideas.lego.com", "multiplayer.it", "rebrickable.com", "twitter.com",
    "x.com", "brothers-brick.com", "everyeye.it", "facebook.com",
    "figuresinaction.com", "flickr.com", "instagram.com", "lego.com",
    "lercio.it", "youtube.com", "youtube-nocookie.com", "youtu.be",
})


def _is_allowed_domain(netloc: str) -> bool:
    return any(d in netloc for d in _ALLOWED_DOMAINS)


def extract_and_normalize_urls(text: str) -> list[tuple[str, str]]:
    """Return list of (original_url, normalized_url) pairs found in text."""
    raw_urls = _URL_RE.findall(text)
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw in raw_urls:
        raw = _TRAILING_PUNCT.sub("", raw)
        normalized = _normalize(raw)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append((raw, normalized))
    return result


def _normalize(url: str) -> str | None:
    try:
        parsed = urlparse(url)
    except Exception:
        return url

    netloc = parsed.netloc.lower()

    if not _is_allowed_domain(netloc):
        return None

    if _is_youtube(netloc):
        return _normalize_youtube(parsed) or _generic_normalize(parsed)
    if _is_instagram(netloc):
        return _normalize_instagram(parsed) or _generic_normalize(parsed)
    if _is_facebook(netloc):
        return _normalize_facebook(parsed) or _generic_normalize(parsed)
    if _is_9gag(netloc):
        return _normalize_9gag(parsed) or _generic_normalize(parsed)
    return _generic_normalize(parsed)


# ── YouTube ──────────────────────────────────────────────────────────────────

def _is_youtube(netloc: str) -> bool:
    return any(d in netloc for d in ("youtube.com", "youtu.be", "youtube-nocookie.com"))


def _normalize_youtube(parsed) -> str | None:
    netloc = parsed.netloc.lower()
    path = parsed.path

    video_id = None

    if "youtu.be" in netloc:
        # https://youtu.be/VIDEO_ID
        video_id = path.strip("/").split("/")[0] or None
    else:
        qs = parse_qs(parsed.query)
        if "/watch" in path:
            # https://www.youtube.com/watch?v=VIDEO_ID
            video_id = (qs.get("v") or [None])[0]
        elif "/shorts/" in path:
            # https://www.youtube.com/shorts/VIDEO_ID
            parts = [p for p in path.split("/") if p]
            idx = parts.index("shorts") if "shorts" in parts else -1
            if idx >= 0 and idx + 1 < len(parts):
                video_id = parts[idx + 1]
        elif "/embed/" in path:
            parts = [p for p in path.split("/") if p]
            idx = parts.index("embed") if "embed" in parts else -1
            if idx >= 0 and idx + 1 < len(parts):
                video_id = parts[idx + 1]
        elif "/v/" in path:
            parts = [p for p in path.split("/") if p]
            idx = parts.index("v") if "v" in parts else -1
            if idx >= 0 and idx + 1 < len(parts):
                video_id = parts[idx + 1]
        else:
            # Fallback: try query param v
            video_id = (qs.get("v") or [None])[0]

    if not video_id:
        return None

    # Strip anything after '?' or '&' in the video ID itself (edge cases)
    video_id = video_id.split("?")[0].split("&")[0].split("#")[0]
    if not video_id:
        return None

    return f"https://www.youtube.com/watch?v={video_id}"


# ── Instagram ─────────────────────────────────────────────────────────────────

def _is_instagram(netloc: str) -> bool:
    return "instagram.com" in netloc


_INSTAGRAM_CONTENT_TYPES = ("p", "reel", "reels", "tv")


def _normalize_instagram(parsed) -> str | None:
    parts = [p for p in parsed.path.split("/") if p]
    for i, part in enumerate(parts):
        if part in _INSTAGRAM_CONTENT_TYPES and i + 1 < len(parts):
            content_type = "reel" if part == "reels" else part
            content_id = parts[i + 1]
            return f"https://www.instagram.com/{content_type}/{content_id}/"
    return None


# ── Facebook ──────────────────────────────────────────────────────────────────

def _is_facebook(netloc: str) -> bool:
    return "facebook.com" in netloc or "fb.watch" in netloc or "fb.me" in netloc


def _normalize_facebook(parsed) -> str | None:
    netloc = parsed.netloc.lower()
    path = parsed.path

    # fb.watch short links
    if "fb.watch" in netloc or "fb.me" in netloc:
        short_id = path.strip("/").split("/")[0]
        if short_id:
            host = "fb.watch" if "fb.watch" in netloc else "fb.me"
            return f"https://{host}/{short_id}"
        return None

    qs = parse_qs(parsed.query)
    parts = [p for p in path.split("/") if p]

    # /watch/?v=ID  or  /watch/ID
    if parts and parts[0] == "watch":
        vid = (qs.get("v") or [None])[0]
        if vid:
            return f"https://www.facebook.com/watch/?v={vid}"
        return None

    # /video/ID  or  /videos/ID
    if len(parts) >= 2 and parts[-2] in ("video", "videos"):
        vid = parts[-1]
        return f"https://www.facebook.com/videos/{vid}/"

    # /photo/?fbid=ID  or  /photo/ID
    if parts and parts[0] == "photo":
        fbid = (qs.get("fbid") or [None])[0]
        if fbid:
            return f"https://www.facebook.com/photo/?fbid={fbid}"
        if len(parts) >= 2:
            return f"https://www.facebook.com/photo/{parts[1]}/"
        return None

    # /permalink/ID/  or  /permalink.php?story_fbid=ID&id=PAGE
    if parts and parts[0] == "permalink":
        story = (qs.get("story_fbid") or [None])[0]
        page = (qs.get("id") or [None])[0]
        if story and page:
            return f"https://www.facebook.com/permalink.php?id={page}&story_fbid={story}"
        if len(parts) >= 2:
            return f"https://www.facebook.com/permalink/{parts[1]}/"
        return None

    # Generic Facebook: strip m. prefix, remove tracking params, reconstruct
    clean_netloc = re.sub(r'^(m|l)\.', 'www.', netloc)
    if not clean_netloc.startswith("www."):
        clean_netloc = "www." + clean_netloc
    filtered_qs = {k: v for k, v in qs.items() if k not in _TRACKING_PARAMS}
    new_query = urlencode(sorted(filtered_qs.items()), doseq=True)
    return urlunparse(("https", clean_netloc, path, "", new_query, ""))


# ── 9gag ──────────────────────────────────────────────────────────────────────

def _is_9gag(netloc: str) -> bool:
    return "9gag.com" in netloc


def _normalize_9gag(parsed) -> str | None:
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2 and parts[0] == "gag":
        return f"https://9gag.com/gag/{parts[1]}"
    return None


# ── Generic fallback ──────────────────────────────────────────────────────────

def _generic_normalize(parsed) -> str:
    scheme = "https"
    netloc = parsed.netloc.lower()
    path = parsed.path
    qs = parse_qs(parsed.query, keep_blank_values=True)
    filtered = {k: v for k, v in qs.items() if k not in _TRACKING_PARAMS}
    new_query = urlencode(sorted(filtered.items()), doseq=True)
    return urlunparse((scheme, netloc, path, "", new_query, ""))
