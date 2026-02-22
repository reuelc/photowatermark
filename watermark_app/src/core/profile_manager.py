"""
profile_manager.py — Save, load, and list named watermark configuration profiles.

Profiles are stored as plain JSON files inside /profiles/.
A special file "_last_used.json" persists settings between sessions.

Future extension points:
  • Swap the JSON file backend for a SQLite DB or cloud KV store.
  • Add profile import/export (zip bundle with fonts / logo).
"""

import os
import json

from .constants import PROFILES_DIR, LAST_USED_FILE, DEFAULT_CONFIG


class ProfileManager:
    """
    Manages named profiles stored as JSON files.

    Profile files are named  <safe_name>.json  where spaces are replaced
    with underscores so the filenames stay cross-platform safe.
    """

    def __init__(self):
        os.makedirs(PROFILES_DIR, exist_ok=True)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _safe_name(self, name: str) -> str:
        """Convert a human-readable profile name to a safe filename stem."""
        return name.strip().replace(" ", "_").replace("/", "_").replace("\\", "_")

    def _path(self, name: str) -> str:
        return os.path.join(PROFILES_DIR, f"{self._safe_name(name)}.json")

    def _merge_with_defaults(self, saved: dict) -> dict:
        """
        Merge a saved profile with DEFAULT_CONFIG so that new config keys
        added in future versions are always present with sensible defaults.
        """
        merged = DEFAULT_CONFIG.copy()
        merged.update(saved)
        return merged

    # ── Named profiles ────────────────────────────────────────────────────────

    def save(self, name: str, config: dict) -> None:
        """Persist *config* under *name*."""
        with open(self._path(name), "w", encoding="utf-8") as fh:
            json.dump(config, fh, indent=2, ensure_ascii=False)

    def load(self, name: str) -> dict:
        """
        Load the named profile.  Returns a dict merged with DEFAULT_CONFIG
        so missing keys are always populated.
        """
        path = self._path(name)
        if not os.path.exists(path):
            return DEFAULT_CONFIG.copy()
        with open(path, "r", encoding="utf-8") as fh:
            saved = json.load(fh)
        return self._merge_with_defaults(saved)

    def delete(self, name: str) -> None:
        """Delete the named profile file if it exists."""
        path = self._path(name)
        if os.path.exists(path):
            os.remove(path)

    def list_profiles(self) -> list:
        """Return a sorted list of saved profile names (human-readable)."""
        names = []
        for fname in os.listdir(PROFILES_DIR):
            if fname.endswith(".json") and not fname.startswith("_"):
                human = os.path.splitext(fname)[0].replace("_", " ")
                names.append(human)
        return sorted(names)

    # ── Last-used settings ────────────────────────────────────────────────────

    def save_last_used(self, config: dict) -> None:
        """Overwrite the last-used settings file."""
        with open(LAST_USED_FILE, "w", encoding="utf-8") as fh:
            json.dump(config, fh, indent=2, ensure_ascii=False)

    def load_last_used(self) -> dict:
        """
        Load last-used settings.
        Returns DEFAULT_CONFIG on first run (file doesn't exist yet).
        """
        if not os.path.exists(LAST_USED_FILE):
            return DEFAULT_CONFIG.copy()
        with open(LAST_USED_FILE, "r", encoding="utf-8") as fh:
            saved = json.load(fh)
        return self._merge_with_defaults(saved)
