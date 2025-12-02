import logging
import os


def get_secret(name: str, *, required: bool = True, default: str | None = None) -> str:
    val = os.getenv(name, default if default is not None else None)
    if required and (val is None or val == ""):
        raise RuntimeError(f"Missing required secret: {name}")
    return val or ""


class SecretMaskingFilter(logging.Filter):
    def __init__(self, *secret_names: str):
        super().__init__()
        self._values = {os.getenv(n) for n in secret_names if os.getenv(n)}
        self._keys = set(secret_names)

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for v in list(self._values):
            if v and v in msg:
                msg = msg.replace(v, "***")
        for k in self._keys:
            if k in msg:
                msg = msg.replace(k, f"{k}=***")
        record.msg = msg
        record.args = ()
        return True


def install_secret_filter(logger: logging.Logger, *secret_names: str) -> None:
    logger.addFilter(SecretMaskingFilter(*secret_names))
