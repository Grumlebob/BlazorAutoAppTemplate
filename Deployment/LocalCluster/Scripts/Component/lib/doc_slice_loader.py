"""Load only explicitly declared, reachable deployment documentation slices."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping, Sequence
from urllib.parse import unquote, urlsplit


CLUSTER_ENTRY = "Deployment/LocalCluster/HowToDeployLocalCluster.md"
FORK_ENTRY = "docs/HowToForkThisRepo.md"

ENTRY_DOCUMENT_ROOTS: dict[str, tuple[str, ...]] = {
    CLUSTER_ENTRY: ("Deployment/LocalCluster", "Deployment/Common"),
    FORK_ENTRY: ("docs", "Deployment/LocalCluster", "Deployment/Common"),
}

DOC_OWNER_SLICES: dict[str, tuple[str, tuple[str, ...]]] = {
    # Add an entry path when a documentation-movement packet creates a slice.
    "setup": ("Deployment/LocalCluster/Setup.md", ()),
    "settings": ("Deployment/LocalCluster/Settings.md", ()),
    "fork_existing": ("Deployment/LocalCluster/ForkExistingCluster.md", ()),
    "operations": ("Deployment/LocalCluster/Operations.md", ()),
    "ssh_trust": ("Deployment/Common/SshTrust.md", ()),
    "release_contract": ("Deployment/Common/ReleaseContract.md", ()),
}

DOC_OWNER_PATHS: dict[str, str] = {
    owner: path for owner, (path, _) in DOC_OWNER_SLICES.items()
}

# Derive per-entry declarations from the same owner rows used by the audit.
DOC_ENTRY_SLICES: dict[str, tuple[str, ...]] = {
    entry_path: tuple(
        path
        for path, entries in DOC_OWNER_SLICES.values()
        if entry_path in entries
    )
    for entry_path in (CLUSTER_ENTRY, FORK_ENTRY)
}

_MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(\s*(?:<([^>]+)>|([^\s)]+))")
_FENCE_START = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_TARGET_SCRIPT_PATTERNS = (
    re.compile(r"(?:\./)?Deployment/LocalCluster/Scripts/([A-Za-z0-9_.-]+\.sh)"),
    re.compile(r"`([A-Za-z0-9_.-]+\.sh)`"),
)


class DocumentSliceError(ValueError):
    """An invalid or unreachable documentation-slice declaration."""


def _allowed_roots(repo_root: Path, entry_path: str) -> tuple[Path, ...]:
    roots = ENTRY_DOCUMENT_ROOTS.get(entry_path)
    if roots is None:
        raise DocumentSliceError(f"{entry_path}: no documentation roots are allowed for this entry")
    return tuple((repo_root / root).resolve() for root in roots)


def _validate_document_path(
    repo_root: Path,
    entry_path: str,
    candidate: str,
    allowed_roots: Sequence[Path],
) -> str:
    normalized = candidate.replace("\\", "/")
    if not normalized or normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
        raise DocumentSliceError(f"{candidate}: documentation path must be repository-relative")
    if any(part == ".." for part in normalized.split("/")):
        raise DocumentSliceError(f"{candidate}: parent traversal is not allowed in documentation paths")
    if Path(normalized).suffix.lower() not in {".md", ".mdx"}:
        raise DocumentSliceError(f"{candidate}: declared documentation slices must be Markdown files")

    root = repo_root.resolve()
    resolved = (root / normalized).resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise DocumentSliceError(f"{candidate}: path resolves outside the repository") from exc

    if not any(resolved.is_relative_to(allowed_root) for allowed_root in allowed_roots):
        raise DocumentSliceError(
            f"{candidate}: path is outside the allowed documentation roots for {entry_path}"
        )
    return relative.as_posix()


def _markdown_without_fences(markdown: str) -> str:
    visible: list[str] = []
    fence_char: str | None = None
    fence_size = 0

    for line in markdown.splitlines():
        match = _FENCE_START.match(line)
        if fence_char is None:
            if match:
                marker = match.group(1)
                fence_char = marker[0]
                fence_size = len(marker)
            else:
                visible.append(line)
            continue

        if re.fullmatch(
            rf" {{0,3}}{re.escape(fence_char)}{{{fence_size},}}[ \t]*",
            line,
        ):
            fence_char = None
            fence_size = 0

    text = "\n".join(visible)
    return _without_inline_code(text)


def _without_inline_code(markdown: str) -> str:
    """Remove matched backtick code spans before checking Markdown links."""
    visible: list[str] = []
    index = 0
    while index < len(markdown):
        if markdown[index] != "`":
            visible.append(markdown[index])
            index += 1
            continue

        run_end = index
        while run_end < len(markdown) and markdown[run_end] == "`":
            run_end += 1
        run_size = run_end - index
        closing = run_end
        while True:
            closing = markdown.find("`" * run_size, closing)
            if closing < 0:
                visible.append(markdown[index:run_end])
                index = run_end
                break
            before = closing > 0 and markdown[closing - 1] == "`"
            after_index = closing + run_size
            after = after_index < len(markdown) and markdown[after_index] == "`"
            if before or after:
                closing += 1
                continue
            visible.append(" ")
            index = after_index
            break

    return "".join(visible)


def _linked_markdown_paths(repo_root: Path, source_path: str, markdown: str) -> set[str]:
    targets: set[str] = set()
    for match in _MARKDOWN_LINK.finditer(_markdown_without_fences(markdown)):
        destination = match.group(1) or match.group(2) or ""
        parsed = urlsplit(destination)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        decoded_path = unquote(parsed.path)
        if Path(decoded_path).suffix.lower() not in {".md", ".mdx"}:
            continue
        source = repo_root / source_path
        resolved = (source.parent / decoded_path).resolve()
        try:
            relative = resolved.relative_to(repo_root.resolve())
        except ValueError:
            continue
        targets.add(relative.as_posix())
    return targets


def load_document_slices(
    repo_root: Path,
    entry_path: str,
    declarations: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, str]:
    """Read an entry and its declared slices, rejecting absent or unreachable files."""
    selected_declarations = DOC_ENTRY_SLICES if declarations is None else declarations
    if entry_path not in selected_declarations:
        raise DocumentSliceError(f"{entry_path}: no documentation-slice declaration exists for this entry")

    root = repo_root.resolve()
    allowed_roots = _allowed_roots(root, entry_path)
    normalized_entry = _validate_document_path(root, entry_path, entry_path, allowed_roots)
    entry_file = root / normalized_entry
    if not entry_file.is_file():
        raise DocumentSliceError(f"{normalized_entry}: required documentation entry is missing")

    declared_paths = list(selected_declarations[entry_path])
    if len(declared_paths) != len(set(declared_paths)):
        raise DocumentSliceError(f"{entry_path}: documentation-slice declaration contains a duplicate path")

    normalized_slices = [
        _validate_document_path(root, entry_path, path, allowed_roots)
        for path in declared_paths
    ]
    if normalized_entry in normalized_slices:
        raise DocumentSliceError(f"{entry_path}: the entry cannot also be declared as its own slice")

    documents = {normalized_entry: entry_file.read_text(encoding="utf-8-sig")}
    for path in normalized_slices:
        slice_file = root / path
        if not slice_file.is_file():
            raise DocumentSliceError(f"{path}: declared documentation slice does not exist")
        documents[path] = slice_file.read_text(encoding="utf-8-sig")

    declared_set = set(normalized_slices)
    reachable = {normalized_entry}
    pending = [normalized_entry]
    while pending:
        source_path = pending.pop()
        for linked_path in _linked_markdown_paths(root, source_path, documents[source_path]):
            if linked_path in declared_set and linked_path not in reachable:
                reachable.add(linked_path)
                pending.append(linked_path)

    unreachable = sorted(declared_set - reachable)
    if unreachable:
        path = unreachable[0]
        raise DocumentSliceError(f"{entry_path}: declared documentation slice is unreachable: {path}")

    return documents


def effective_document_path(
    documents: Mapping[str, str],
    entry_path: str,
    owner_path: str,
) -> str:
    """Use a loaded owner slice, or retain the root entry as the transition fallback."""
    if owner_path in documents:
        return owner_path
    if entry_path in documents:
        return entry_path
    raise DocumentSliceError(f"{entry_path}: required documentation entry was not loaded")


def missing_literal(
    documents: Mapping[str, str],
    entry_path: str,
    owner_path: str,
    literal: str,
    reason: str,
) -> str | None:
    """Return an actionable missing-rule message for the effective owner, if any."""
    path = effective_document_path(documents, entry_path, owner_path)
    if literal in documents[path]:
        return None
    return f"{path}: missing {reason}: {literal}"


def missing_section_literal(
    documents: Mapping[str, str],
    entry_path: str,
    owner_path: str,
    section_start: str,
    section_end: str,
    literal: str,
    reason: str,
) -> str | None:
    """Require a literal inside a bounded section of its effective owner."""
    path = effective_document_path(documents, entry_path, owner_path)
    text = documents[path]
    start = text.find(section_start)
    if start < 0:
        return f"{path}: missing {reason} section: {section_start}"
    end = text.find(section_end, start + len(section_start))
    if end < 0:
        return f"{path}: missing end of {reason} section: {section_end}"
    if literal not in text[start:end]:
        return f"{path}: missing {reason}: {literal}"
    return None


def fence_error(document_path: str, markdown: str) -> str | None:
    fence_char: str | None = None
    fence_size = 0
    for line in markdown.splitlines():
        match = _FENCE_START.match(line)
        if fence_char is None:
            if match:
                marker = match.group(1)
                fence_char = marker[0]
                fence_size = len(marker)
            continue

        if re.fullmatch(
            rf" {{0,3}}{re.escape(fence_char)}{{{fence_size},}}[ \t]*",
            line,
        ):
            fence_char = None
            fence_size = 0

    if fence_char is not None:
        return f"{document_path}: unbalanced markdown code fences"
    return None


def missing_target_scripts(repo_root: Path, document_path: str, markdown: str) -> list[str]:
    """Return path-qualified errors for missing scripts referenced by one document."""
    names = set().union(*(pattern.findall(markdown) for pattern in _TARGET_SCRIPT_PATTERNS))
    missing = []
    for name in sorted(names):
        target = f"Deployment/LocalCluster/Scripts/{name}"
        if not (repo_root / target).is_file():
            missing.append(f"{document_path}: references missing script: {target}")
    return missing
