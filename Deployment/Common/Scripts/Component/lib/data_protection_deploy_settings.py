from __future__ import annotations


LEGACY_DATA_PROTECTION_SETTING_KEYS = {
    "data_protection_legacy_key_store",
    "data_protection_legacy_redis_key",
}


def validate_legacy_data_protection_settings(values: dict[str, object]) -> list[str]:
    """Validate the optional one-time legacy key source used by account deployments."""
    errors: list[str] = []
    store = values.get("data_protection_legacy_key_store", "None")
    redis_key = values.get("data_protection_legacy_redis_key", "")

    if not isinstance(store, str) or store not in {"None", "Redis", "FileSystem"}:
        errors.append("data_protection_legacy_key_store must be None, Redis, or FileSystem")
        return errors
    if not isinstance(redis_key, str):
        errors.append("data_protection_legacy_redis_key must be text")
        return errors
    if any(char in redis_key for char in "\r\n\0"):
        errors.append("data_protection_legacy_redis_key must be a single-line value")
    if store == "Redis" and not redis_key:
        errors.append("data_protection_legacy_redis_key is required when the legacy key store is Redis")
    if store != "Redis" and redis_key:
        errors.append("data_protection_legacy_redis_key requires the legacy key store to be Redis")
    return errors
