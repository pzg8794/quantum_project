"""Canonical, finite JSON identities shared by components and orchestration."""
from hashlib import sha256
import json


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()
