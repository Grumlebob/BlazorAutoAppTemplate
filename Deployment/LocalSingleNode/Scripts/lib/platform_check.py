"""Native Linux only: controller WSL is never a deployment node."""
import os
from ls_settings import command


def native():
    return command("uname", "-s") == "Linux" and "microsoft" not in command("uname", "-r").lower() and not any(os.environ.get(key) for key in ("WSL_INTEROP", "WSL_DISTRO_NAME"))


if __name__ == "__main__":
    if not native():
        raise SystemExit("Run node setup on the intended native Linux PC; Windows and WSL are unsupported.")
