"""Loader for the paragraph library, letter types and lexicons."""
from __future__ import annotations

import functools
import pathlib

import yaml

ROOT = pathlib.Path(__file__).parent


@functools.lru_cache(maxsize=None)
def _load(relative: str):
    return yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))


def paragraphs() -> dict[str, dict]:
    return {p["id"]: p for p in _load("paragraphs.yaml")}


def letter_types() -> dict[str, dict]:
    return {t["id"]: t for t in _load("letter_types.yaml")}


def terminology() -> list[dict]:
    return _load("lexicons/terminology.yaml")


def tone() -> dict:
    return _load("lexicons/tone.yaml")


def vocabulary() -> set[str]:
    """Capitalised words the library itself uses -- fed to the PII scanner so
    house vocabulary is never mistaken for an invented name."""
    words: set[str] = set()
    for para in paragraphs().values():
        for word in para["text"].split():
            stripped = word.strip(".,;:()[]'\"")
            if stripped[:1].isupper() and stripped.isalpha():
                words.add(stripped)
    return words
