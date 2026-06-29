from __future__ import annotations

import hashlib

import lxml.html

_SKELETON_TEXT_MAX = 40


def _parse(html: str):
    try:
        return lxml.html.fromstring(html)
    except Exception:
        return None


def build_skeleton(html: str, max_nodes: int = 400) -> str:
    """Compact structural outline: tag + #id/.class/[role], text stripped/truncated."""
    root = _parse(html)
    if root is None:
        return ""
    lines: list[str] = []
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        token = el.tag
        if el.get("id"):
            token += f"#{el.get('id')}"
        cls = el.get("class")
        if cls:
            token += "." + ".".join(cls.split()[:3])
        if el.get("role"):
            token += f"[role={el.get('role')}]"
        text = (el.text or "").strip()
        if text:
            snippet = text[:_SKELETON_TEXT_MAX] + ("…" if len(text) > _SKELETON_TEXT_MAX else "")
            token += f"  «{snippet}»"
        lines.append(token)
        if len(lines) >= max_nodes:
            break
    return "\n".join(lines)


def template_fingerprint(html: str, max_nodes: int = 200) -> str:
    """Stable hash of DOM shape (tags + id/class, text ignored) for rule caching."""
    root = _parse(html)
    if root is None:
        return "empty"
    parts: list[str] = []
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        cls = el.get("class") or ""
        parts.append(f"{el.tag}#{el.get('id') or ''}.{'.'.join(sorted(cls.split()))}")
        if len(parts) >= max_nodes:
            break
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()
