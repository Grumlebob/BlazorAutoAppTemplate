from __future__ import annotations

import re


ACCOUNT_SETTING_KEYS = {
    "accounts_enabled",
    "accounts_registration_enabled",
    "accounts_admin_seed_enabled",
    "accounts_admin_seed_email",
    "accounts_public_origin",
    "accounts_email_host",
    "accounts_email_port",
    "accounts_email_security",
    "accounts_email_from",
}


def _bool_setting(values: dict[str, object], key: str, errors: list[str]) -> bool:
    value = values.get(key, False)
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    errors.append(f"{key} must be true or false")
    return False


def validate_account_deploy_settings(values: dict[str, object]) -> list[str]:
    """Validate public account deployment settings without inspecting credentials."""
    errors: list[str] = []
    enabled = _bool_setting(values, "accounts_enabled", errors)
    registration = _bool_setting(values, "accounts_registration_enabled", errors)
    seed_enabled = _bool_setting(values, "accounts_admin_seed_enabled", errors)

    text_keys = (
        "accounts_admin_seed_email",
        "accounts_public_origin",
        "accounts_email_host",
        "accounts_email_from",
    )
    text: dict[str, str] = {}
    for key in text_keys:
        value = values.get(key, "")
        if not isinstance(value, str):
            errors.append(f"{key} must be text")
            continue
        text[key] = value
        if any(char in value for char in "\r\n\0"):
            errors.append(f"{key} must be a single-line value")

    port_value = values.get("accounts_email_port", 587)
    try:
        port = int(port_value) if not isinstance(port_value, bool) else 0
    except (TypeError, ValueError):
        port = 0
    if not 1 <= port <= 65535:
        errors.append("accounts_email_port must be an integer from 1 through 65535")

    security = values.get("accounts_email_security", "StartTls")
    if security not in {"StartTls", "SslOnConnect"}:
        errors.append("accounts_email_security must be StartTls or SslOnConnect")

    origin = text.get("accounts_public_origin", "")
    if origin and not re.fullmatch(r"https://[^/?#]+/?", origin, flags=re.IGNORECASE):
        errors.append("accounts_public_origin must be a bare HTTPS origin")

    host = text.get("accounts_email_host", "")
    sender = text.get("accounts_email_from", "")
    admin_email = text.get("accounts_admin_seed_email", "")
    if registration and (not enabled or not host or not sender or not origin):
        errors.append("accounts_registration_enabled requires enabled accounts and complete email settings")
    if seed_enabled and (not enabled or not admin_email):
        errors.append("accounts_admin_seed_enabled requires enabled accounts and an Admin seed email")
    if host and (not enabled or not sender or not origin):
        errors.append("accounts_email_host requires enabled accounts, a sender and a public origin")
    if not host and sender:
        errors.append("accounts_email_from requires accounts_email_host")

    return errors
