"""Bind prepared campaign content to the same saved UIDs as ENEMY_P2."""
from __future__ import annotations

from collections.abc import Mapping


def resolve_actor_bindings(manifest, explicit=None):
    """Return a complete, unique actor map before any private staging writes.

    Automatic binding requires validated, known campaign generator UIDs. Custom
    fixture targets remain explicit; decimal-looking tokens alone are not proof
    that a fixture uses campaign generator UIDs.
    """
    from .seed import validate

    validate(manifest)
    layout = manifest.get("p2_layout")
    if not layout:
        if explicit is not None:
            raise ValueError("actor bindings require a P2 layout")
        return {}
    targets = [binding["target"] for binding in layout["bindings"]]
    if len(set(targets)) != len(targets):
        raise ValueError("duplicate actor target")

    from .seed import _default_admitted_placement, _default_proxy_placement

    known = {row["uid"] for row in _default_admitted_placement()["slots"]}
    if manifest.get("p2_proxy_tier"):
        known.update(row["uid"] for row in _default_proxy_placement()["slots"])
    campaign = "enemy_catalog" in manifest or all(
        target.isascii() and target.isdecimal() and str(int(target)) == target
        and int(target) in known for target in targets)
    expected = {}
    if campaign:
        catalog = manifest.get("enemy_catalog")
        sources = {row["uid"]: row for row in catalog["sources"]} if catalog else None
        for binding in layout["bindings"]:
            target = binding["target"]
            if not target.isascii() or not target.isdecimal():
                raise ValueError("campaign actor target must be a generator UID")
            uid = int(target)
            if str(uid) != target or not 0 < uid < 2**32:
                raise ValueError("campaign actor UID must be canonical uint32")
            source = sources.get(uid) if sources is not None else None
            if sources is not None and (source is None or source["game"] not in ("p2", "proxy")
                    or source["species"] != binding["source_id"]):
                raise ValueError("campaign actor UID differs from the saved final source")
            expected[target] = uid

    if explicit is None:
        if not campaign:
            raise ValueError("custom P2 layout requires explicit actor bindings")
        return expected
    if not isinstance(explicit, Mapping) or set(explicit) != set(targets):
        raise ValueError("actor bindings must cover exactly the saved targets")
    result = dict(explicit)
    if any(type(uid) is not int or not 0 < uid < 2**32 for uid in result.values()):
        raise ValueError("actor generators must be uint32 integers")
    if len(set(result.values())) != len(result):
        raise ValueError("actor generators must be unique")
    if campaign and result != expected:
        raise ValueError("campaign actor bindings must match saved generator UIDs")
    return result
