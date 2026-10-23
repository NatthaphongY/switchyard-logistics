# -*- coding: utf-8 -*-
"""Gate: the tree must be publishable as it stands (2026-10-23).

Why this gate exists
--------------------
The owner asked for a check that no real name, phone number, or private path has
leaked into the repository before the tree is pushed to a public repository. A
one-off grep answers that question for one afternoon. This test answers it for
every future commit, and it fails on the same classes of leak.

Scope is deliberate: the check runs on the *public surface*, meaning every file
in this repository that git would actually commit. Build output such as
`engine/target/` is git-ignored and recorded there with the host
toolchain path in it; it must never be committed, and the ignore rule is
asserted here rather than trusted.

What is treated as a leak
-------------------------
1. E-mail addresses.
2. Phone numbers, in international or Thai national form.
3. Personal or host-specific paths: `C:/Users/...`, `/home/<name>`, OneDrive,
   AppData, `%USERPROFILE%`, or any drive-letter absolute path.
4. Personal names. The list of names to protect is stored as truncated
   SHA-256 digests, so this guard does not itself publish the names it exists to
   keep out of the repository. A word of four or more characters is hashed and
   compared against a fixed set.
5. Vendor and third-party product tokens that belong to another project
   (`HCL.Core`, `HclRandom`, `Fixed32`, `Centurion's Legacy`). The mechanism may
   be described; the other project's identity is not published.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT
SUFFIXES = {".py", ".md", ".json", ".txt", ".rs", ".toml", ".yaml", ".yml", ".ps1", ".csv"}
DIGEST_CHARS = 16

LEAK_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone_intl": re.compile(r"\+\d{8,15}\b"),
    "phone_thai": re.compile(r"\b0[689]\d{8}\b"),
    "phone_dashed": re.compile(r"\b\d{3}[-.]\d{3}[-.]\d{4}\b"),
    "host_path": re.compile(
        r"(?:[A-Za-z]:[\\/](?:Users|Documents|Desktop|OneDrive|AppData)\b"
        r"|/home/[A-Za-z0-9._-]+/|%USERPROFILE%|/Users/[A-Za-z0-9._-]+/)"
    ),
    "drive_absolute": re.compile(r"(?<![A-Za-z0-9_<])[A-Za-z]:[\\/][A-Za-z]"),
    "vendor_token": re.compile(r"\b(?:HCL\.Core|HclRandom|Fixed32|Centurion's Legacy)\b"),
}

# Truncated digests of the owner's name and of the local account name. Hashed on
# purpose: a guard that lists the names in plain text is itself the leak.
PERSONAL_NAME_DIGESTS = frozenset({"e8a887fcd8517bdf", "a2a2f60cd47ac3f7", "0a4d20c6aead3bdf"})
WORD = re.compile(r"[A-Za-z][A-Za-z._-]{3,}")


def _digest(word: str) -> str:
    return hashlib.sha256(word.lower().encode("utf-8")).hexdigest()[:DIGEST_CHARS]


def _name_hits(line: str, digests=frozenset(PERSONAL_NAME_DIGESTS)) -> list:
    return [word for word in WORD.findall(line) if _digest(word) in digests]



def _tracked_or_unignored(path: Path) -> bool:
    """True when git would publish this file.

    `git check-ignore` answers for the current working tree, so a build cache is
    excluded exactly as it would be excluded from the commit.
    """
    if "__pycache__" in path.parts:
        return False
    result = subprocess.run(
        ["git", "check-ignore", "-q", "--", str(path)],
        cwd=ROOT,
        capture_output=True,
    )
    return result.returncode != 0


def _public_files():
    instrument = Path(__file__).resolve()
    for path in sorted(RESEARCH.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUFFIXES:
            continue
        # The leak patterns must contain a sample address, sample number and vendor token
        # to work at all, so this module cannot pass its own scan. The exemption is one
        # file, resolved by path, and it is stated rather than inferred from a name.
        if path.resolve() == instrument:
            continue
        if _tracked_or_unignored(path):
            yield path


def _scan() -> list:
    findings = []
    for path in _public_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        relative = path.relative_to(ROOT).as_posix()
        for number, line in enumerate(text.splitlines(), 1):
            for label, pattern in LEAK_PATTERNS.items():
                match = pattern.search(line)
                if match:
                    findings.append(f"{relative}:{number}:{label}:{match.group(0)[:60]}")
            for name in _name_hits(line):
                findings.append(f"{relative}:{number}:personal_name:{len(name)} chars")
    return findings



def test_no_personal_data_in_the_publishable_research_tree():
    findings = _scan()
    assert findings == [], (
        "personal or third-party data in this repository (see docstring for the classes):\n"
        + "\n".join(findings[:20])
    )


def test_build_output_is_ignored_so_host_paths_cannot_be_committed():
    """`engine/target` is Cargo output; it records the host toolchain path."""
    result = subprocess.run(
        ["git", "check-ignore", "-q", "--", "engine/target/.rustc_info.json"],
        cwd=ROOT,
        capture_output=True,
    )
    assert result.returncode == 0, "build output must stay out of the published tree"


def test_documents_do_not_name_the_third_party_engine():
    """The mechanism is described; another project's identity is not published."""
    offenders = [
        path.relative_to(ROOT).as_posix()
        for path in _public_files()
        if LEAK_PATTERNS["vendor_token"].search(
            path.read_text(encoding="utf-8", errors="replace")
        )
    ]
    assert offenders == [], f"vendor tokens still present: {offenders}"


def test_patterns_actually_detect_a_known_bad_line():
    """A gate that cannot fail is not a gate: prove each pattern fires."""
    sample = (
        "contact someone@example.com or +66812345678 or 081-234-5678 or 0812345678; "
        "path C:/Users/someone/project and D:/the host system; "
        "engine HclRandom from HCL.Core"
    )
    hits = {label for label, pattern in LEAK_PATTERNS.items() if pattern.search(sample)}
    assert hits == set(LEAK_PATTERNS), f"patterns that did not fire: {set(LEAK_PATTERNS) - hits}"


def test_the_name_check_fires_without_publishing_the_names():
    """The digest list is enough to catch a name, and carries no plain text."""
    dummy = "exampleowner"
    digests = frozenset({_digest(dummy)})
    assert _name_hits("written by ExampleOwner on a laptop", digests) == ["ExampleOwner"]
    assert _name_hits("nothing personal here", digests) == []
    assert all(
        len(entry) == DIGEST_CHARS and set(entry) <= set("0123456789abcdef")
        for entry in PERSONAL_NAME_DIGESTS
    ), "the guard must hold digests, never the names it protects"
