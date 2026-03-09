import argparse
import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, Optional


def _load_email_config(config_path: Optional[Path]) -> Dict[str, Any]:
    cfg: Dict[str, Any] = {}

    if config_path and config_path.exists():
        cfg.update(json.loads(config_path.read_text(encoding="utf-8")))

    for k in [
        "smtp_host",
        "smtp_port",
        "smtp_ssl",
        "username",
        "password",
        "from_addr",
        "to_addr",
    ]:
        env_k = f"MAIL_{k.upper()}"
        if env_k in os.environ and os.environ[env_k]:
            v = os.environ[env_k]
            if k in {"smtp_port"}:
                try:
                    v = int(v)
                except Exception:
                    pass
            if k in {"smtp_ssl"}:
                v = str(v).strip().lower() in {"1", "true", "yes"}
            cfg[k] = v

    # QQ mail defaults
    cfg.setdefault("smtp_host", "smtp.qq.com")
    cfg.setdefault("smtp_port", 465)
    cfg.setdefault("smtp_ssl", True)

    return cfg


def send_email_with_attachment(
    subject: str,
    body: str,
    attachment_path: Path,
    to_addr: str,
    config_path: Optional[Path] = None,
) -> None:
    cfg = _load_email_config(config_path)

    username = cfg.get("username")
    password = cfg.get("password")
    from_addr = cfg.get("from_addr") or username

    if not username or not password or not from_addr:
        raise RuntimeError(
            "Missing email credentials. Set MAIL_USERNAME / MAIL_PASSWORD / MAIL_FROM_ADDR env vars or provide email_config.json. "
            "For QQ邮箱, MAIL_PASSWORD should be the SMTP授权码 (not login password)."
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(body)

    data = attachment_path.read_bytes()
    msg.add_attachment(
        data,
        maintype="application",
        subtype="pdf",
        filename=attachment_path.name,
    )

    host = cfg.get("smtp_host")
    port = int(cfg.get("smtp_port"))
    use_ssl = bool(cfg.get("smtp_ssl"))

    if use_ssl:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context) as server:
            server.login(str(username), str(password))
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(str(username), str(password))
            server.send_message(msg)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", required=True)
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--subject", default="A股复盘")
    parser.add_argument("--body", default="请查收复盘PDF。")
    parser.add_argument("--config", default="")
    args = parser.parse_args()

    cfg_path = Path(args.config).resolve() if args.config else None
    send_email_with_attachment(
        subject=args.subject,
        body=args.body,
        attachment_path=Path(args.pdf).resolve(),
        to_addr=args.to,
        config_path=cfg_path,
    )


if __name__ == "__main__":
    main()
