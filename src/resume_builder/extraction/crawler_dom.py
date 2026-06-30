from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit, urlunsplit

import lxml.html

from .crawler_models import HtmlTagRule, LinkCandidate, NodeAction
from .skeleton import template_fingerprint

_SKIP_SCHEMES = ("mailto:", "tel:", "javascript:", "data:")
_DANGEROUS = re.compile(
    r"(?:^|[/_-])(logout|log-out|signout|delete|remove|destroy|unsubscribe|checkout|cart)(?:$|[/_?&=-])",
    re.IGNORECASE,
)


def _parse(html: str):
    try:
        return lxml.html.fromstring(html)
    except Exception:
        return None


def _selector(el) -> str:
    tag = str(el.tag).lower()
    if el.get("id"):
        return f"{tag}#{el.get('id')}"
    classes = (el.get("class") or "").split()
    if classes:
        return f"{tag}.{classes[0]}"
    if el.get("role"):
        return f"{tag}[role={el.get('role')}]"
    return tag


def _matches(el, selector: str) -> bool:
    selector = selector.strip()
    if not selector or not isinstance(el.tag, str):
        return False
    tag = str(el.tag).lower()
    role_match = re.fullmatch(r"([\w-]+)?\[role=([\w-]+)\]", selector)
    if role_match:
        return (not role_match.group(1) or tag == role_match.group(1).lower()) and (
            el.get("role") == role_match.group(2)
        )
    id_match = re.fullmatch(r"([\w-]+)?#([\w-]+)", selector)
    if id_match:
        return (not id_match.group(1) or tag == id_match.group(1).lower()) and (
            el.get("id") == id_match.group(2)
        )
    class_match = re.fullmatch(r"([\w-]+)?\.([\w-]+)", selector)
    if class_match:
        return (not class_match.group(1) or tag == class_match.group(1).lower()) and (
            class_match.group(2) in (el.get("class") or "").split()
        )
    return tag == selector.lower()


def build_dom_inventory(html: str, base_url: str, max_nodes: int = 500) -> str:
    """Agent observation containing selectors, tag context, and link-bearing structure."""
    root = _parse(html)
    if root is None:
        return ""
    lines: list[str] = []
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        links = []
        if el.tag.lower() == "a" and el.get("href"):
            links.append(urljoin(base_url, el.get("href")))
        else:
            links.extend(
                urljoin(base_url, a.get("href"))
                for a in el.iterdescendants("a")
                if a.get("href")
            )
        text = " ".join(t.strip() for t in el.itertext() if t.strip())[:120]
        attrs = []
        for name in ("id", "class", "role", "aria-label"):
            if el.get(name):
                attrs.append(f"{name}={el.get(name)!r}")
        line = f"selector={_selector(el)!r} tag={el.tag!r}"
        if attrs:
            line += " " + " ".join(attrs)
        if text:
            line += f" text={text!r}"
        if links:
            line += f" descendant_links={len(links)} samples={links[:4]!r}"
        lines.append(line)
        if len(lines) >= max_nodes:
            break
    return "\n".join(lines)


def _canonicalize(url: str) -> str:
    parts = urlsplit(url)
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def safe_same_domain_url(seed_url: str, raw_url: str) -> str | None:
    if not raw_url or raw_url.lower().startswith(_SKIP_SCHEMES):
        return None
    absolute = _canonicalize(urljoin(seed_url, raw_url))
    seed = urlsplit(seed_url)
    target = urlsplit(absolute)
    if target.scheme not in {"http", "https"} or target.netloc.lower() != seed.netloc.lower():
        return None
    if _DANGEROUS.search(target.path) or _DANGEROUS.search(target.query):
        return None
    return absolute


def apply_tag_rules(
    html: str,
    page_url: str,
    seed_url: str,
    rules: list[HtmlTagRule],
) -> tuple[str, list[LinkCandidate]]:
    """Execute only the actions assigned by the AI to HTML selectors."""
    root = _parse(html)
    if root is None:
        return "", []
    ignored = [r for r in rules if r.action == NodeAction.IGNORE]
    for el in list(root.iter()):
        if any(_matches(el, r.selector) for r in ignored):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)

    text_parts: list[str] = []
    links: list[LinkCandidate] = []
    seen_text: set[str] = set()
    seen_links: set[str] = set()
    for rule in rules:
        if rule.action == NodeAction.IGNORE:
            continue
        for el in root.iter():
            if not _matches(el, rule.selector):
                continue
            if rule.action in {NodeAction.EXTRACT, NodeAction.EXTRACT_AND_CRAWL}:
                text = " ".join(t.strip() for t in el.itertext() if t.strip())
                if text and text not in seen_text:
                    seen_text.add(text)
                    text_parts.append(text)
            if rule.action in {NodeAction.CRAWL, NodeAction.EXTRACT_AND_CRAWL}:
                anchors = [el] if el.tag.lower() == "a" else list(el.iterdescendants("a"))
                for anchor in anchors:
                    url = safe_same_domain_url(seed_url, anchor.get("href") or "")
                    if not url or url == _canonicalize(page_url) or url in seen_links:
                        continue
                    seen_links.add(url)
                    links.append(
                        LinkCandidate(
                            url=url,
                            text=" ".join(anchor.itertext()).strip()[:200],
                            source_selector=rule.selector,
                        )
                    )
    return "\n".join(text_parts).strip(), links


def readability_text(html: str) -> str:
    """Generic non-domain fallback used only after both AI attempts fail."""
    root = _parse(html)
    if root is None:
        return ""
    for tag in ("script", "style", "noscript", "template", "nav", "header", "footer", "aside"):
        for el in list(root.iter(tag)):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)
    candidates = root.xpath("//main|//article|//*[@role='main']")
    target = max(candidates, key=lambda el: len(el.text_content()), default=root)
    return "\n".join(
        line.strip() for line in target.text_content().splitlines() if line.strip()
    )


def fingerprint(html: str) -> str:
    return template_fingerprint(html, max_nodes=400)

