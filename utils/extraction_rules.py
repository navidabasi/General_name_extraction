"""Validated Name Extractor rules, independent of Crown Report's algorithms."""

import copy
import json
import logging
import os
import re
import tempfile
import time
from functools import lru_cache

import requests

from utils.extraction_defaults import default_rules

logger = logging.getLogger(__name__)
RULES_URL = "https://name-extractor-config.navid-kill-policy.workers.dev/rules/extraction"
CACHE_PATH = os.path.join(os.path.expanduser("~"), ".name_extractor_rules.json")
_active = default_rules()
_source = "bundled"


def write_json_cache(path, document):
    """Atomic replacement preserves the last good cache if saving is interrupted."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="name_extractor_", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2, ensure_ascii=False)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_rules(document):
    baseline = default_rules()
    if not isinstance(document, dict) or type(document.get("version")) is not int or document["version"] != 1:
        raise ValueError("Name Extractor rules require version: 1")
    if not isinstance(document.get("revision"), str) or not document["revision"].strip():
        raise ValueError("Name Extractor rules require a revision")
    if set(document) != set(baseline):
        raise ValueError("Unexpected or missing Name Extractor rule sections")
    settings = document["settings"]
    if not isinstance(settings, dict) or set(settings) != set(baseline["settings"]):
        raise ValueError("Unexpected or missing extraction settings")
    for key, default in baseline["settings"].items():
        value = settings[key]
        if type(value) is not type(default):
            raise ValueError(f"Invalid type for {key}")
        if isinstance(value, list) and (not value or any(not isinstance(v, str) or not v.strip() for v in value)):
            raise ValueError(f"{key} must contain nonempty strings")
        if isinstance(value, dict) and (not value or any(
            not isinstance(k, str) or not k.strip() or not isinstance(v, str) or not v.strip()
            for k, v in value.items()
        )):
            raise ValueError(f"{key} must map nonempty strings to nonempty strings")
        if isinstance(value, str) and not value.strip():
            raise ValueError(f"{key} must not be empty")
        if type(value) is int and not 0 <= value <= 120:
            raise ValueError(f"Invalid age threshold {key}")
    if not (settings["AGE_CHILD_MAX"] == settings["AGE_YOUTH_MIN"] <=
            settings["AGE_YOUTH_MAX"] == settings["AGE_ADULT_MIN"]):
        raise ValueError("Age thresholds must have consistent child/youth/adult boundaries")
    if settings["GYG_MDA_PLATFORM"] in settings["GYG_STANDARD_PLATFORMS"]:
        raise ValueError("MDA and standard resellers must remain separate")
    for section in ("patterns", "mda_patterns"):
        patterns = document[section]
        if not isinstance(patterns, dict) or set(patterns) != set(baseline[section]):
            raise ValueError(f"Unexpected or missing {section}")
        for key, value in patterns.items():
            if not isinstance(value, dict) or set(value) != {"regex", "flags", "groups"}:
                raise ValueError(f"Invalid pattern {key}")
            if not isinstance(value["regex"], str) or not value["regex"].strip():
                raise ValueError(f"Empty pattern {key}")
            if type(value["flags"]) is not int or value["flags"] < 0 or value["flags"] & ~int(re.I | re.M | re.S | re.X):
                raise ValueError(f"Unsupported regex flags for {key}")
            try:
                pattern = re.compile(value["regex"], value["flags"])
            except re.error as exc:
                raise ValueError(f"Invalid regex for {key}: {exc}") from exc
            expected = baseline[section][key]["groups"]
            if type(value["groups"]) is not int or value["groups"] != expected or pattern.groups != expected:
                raise ValueError(f"{key} must retain {expected} capture groups")
    return copy.deepcopy(document)


def refresh_extraction_rules(timeout=5):
    """Fetch once per run; reject bad updates before activating or caching them."""
    global _active, _source
    try:
        response = requests.get(RULES_URL, timeout=timeout, params={"_": time.time_ns()},
                                headers={"Accept": "application/json", "Cache-Control": "no-cache"})
        response.raise_for_status()
        rules = validate_rules(response.json())
        source = "cloud"
        try:
            write_json_cache(CACHE_PATH, rules)
        except OSError as exc:
            logger.warning("Could not save extraction rules for offline use: %s", exc)
    except (requests.RequestException, OSError, ValueError) as exc:
        logger.warning("Could not refresh Name Extractor rules: %s", exc)
        try:
            with open(CACHE_PATH, encoding="utf-8") as handle:
                rules = validate_rules(json.load(handle))
            source = "cached"
        except (OSError, ValueError) as cache_exc:
            logger.warning("No usable extraction rule cache: %s", cache_exc)
            # Keep a previously validated in-memory download if cache saving failed.
            rules, source = _active, _source
    _active, _source = rules, source
    _compile.cache_clear()
    logger.info("Name Extractor rules: %s; revision %s", source, rules["revision"])
    return rules, source


def get_extraction_rules():
    return _active


def get_extraction_rules_source():
    return _source, _active["revision"]


def get_setting(name):
    if name == "ALL_GYG_PLATFORMS":
        return _active["settings"]["GYG_STANDARD_PLATFORMS"] + [_active["settings"]["GYG_MDA_PLATFORM"]]
    return _active["settings"][name]


@lru_cache(maxsize=128)
def _compile(regex, flags):
    return re.compile(regex, flags)


def get_pattern(section, name):
    rule = _active[section][name]
    return _compile(rule["regex"], rule["flags"])
