import argparse
import sys
import oci
import oci.config
import oci.exceptions

from config import load_config
from checker import is_ip_blocked
from rotator import get_primary_private_ip, get_current_public_ip, rotate_public_ip, RotationError


def main():
    parser = argparse.ArgumentParser(description="Oracle OCI 公网 IP 自动轮换工具")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行，不执行任何 OCI 写操作")
    args = parser.parse_args()

    cfg = load_config(dry_run=args.dry_run)

    try:
        oci_config = oci.config.from_file(profile_name=cfg["config_profile"])
        compute_client = oci.core.ComputeClient(oci_config)
        network_client = oci.core.VirtualNetworkClient(oci_config)
    except Exception as e:
        print(f"[-] OCI 配置初始化失败，请检查 ~/.oci/config。\n报错信息: {e}")
        sys.exit(1)

    try:
        instance = compute_client.get_instance(instance_id=cfg["instance_id"]).data
        compartment_id = instance.compartment_id
    except oci.exceptions.ServiceError as e:
        print(f"[-] 无法获取实例信息，请核对 OCI_INSTANCE_ID。报错: {e.message}")
        sys.exit(1)

    if instance.lifecycle_state != "RUNNING":
        print(f"[-] 实例未处于运行状态 (状态: {instance.lifecycle_state})，中止检测。")
        sys.exit(0)

    primary_private_ip = get_primary_private_ip(
        compute_client, network_client, compartment_id, cfg["instance_id"]
    )

    current_public_ip = get_current_public_ip(network_client, primary_private_ip.id)

    if not current_public_ip:
        print("[-] 当前实例暂无公网 IP，直接申请分配...")
        try:
            rotate_public_ip(network_client, compartment_id, primary_private_ip.id, None, cfg["dry_run"])
        except RotationError as e:
            print(f"[-] {e}")
            sys.exit(1)
        return

    ip_addr = current_public_ip.ip_address
    print(f"[*] 当前公网 IP: {ip_addr}")

    if is_ip_blocked(ip_addr, cfg["check_port"], cfg["check_timeout"]):
        print("\n[!] IP 判定为受阻，触发轮换引擎 [!]\n")
        try:
            rotate_public_ip(
                network_client, compartment_id, primary_private_ip.id,
                current_public_ip, cfg["dry_run"]
            )
        except RotationError as e:
            print(f"[-] {e}")
            sys.exit(1)
    else:
        print("[+] IP 访问正常，无需轮换。")


if __name__ == "__main__":
    main()
