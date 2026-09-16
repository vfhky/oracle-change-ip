import os
import sys
from dotenv import load_dotenv

load_dotenv()


def load_config(dry_run: bool = False) -> dict:
    instance_id = os.environ.get("OCI_INSTANCE_ID", "").strip()
    if not instance_id:
        print("[-] 缺少必填配置 OCI_INSTANCE_ID，请检查 .env 文件。")
        sys.exit(1)

    try:
        check_port = int(os.environ.get("CHECK_PORT", "22"))
    except ValueError:
        print("[-] CHECK_PORT must be an integer.")
        sys.exit(1)

    try:
        check_timeout = int(os.environ.get("CHECK_TIMEOUT", "5"))
    except ValueError:
        print("[-] CHECK_TIMEOUT must be an integer.")
        sys.exit(1)

    return {
        "instance_id": instance_id,
        "config_profile": os.environ.get("OCI_CONFIG_PROFILE", "DEFAULT"),
        "check_port": check_port,
        "check_timeout": check_timeout,
        "dry_run": dry_run,
    }
