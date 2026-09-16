import time
from typing import Optional

import oci
import oci.exceptions
import oci.pagination


class RotationError(Exception):
    """Raised when OCI IP rotation cannot be completed safely."""


def _wait_until_terminated(network_client, public_ip_id: str, max_wait: int = 30):
    """Poll until the public IP resource lifecycle_state becomes TERMINATED."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            ip = network_client.get_public_ip(public_ip_id=public_ip_id).data
            if ip.lifecycle_state == "TERMINATED":
                return
        except oci.exceptions.ServiceError as e:
            if e.status == 404:
                return
            raise
        time.sleep(2)
    print(f"[!] 等待旧 IP {public_ip_id} 释放超时，继续执行...")


def get_primary_private_ip(compute_client, network_client, compartment_id: str, instance_id: str):
    """Return the primary private IP object for the primary VNIC of an instance."""
    print("[*] 正在拉取实例网络结构...")
    vnic_attachments = oci.pagination.list_call_get_all_results(
        compute_client.list_vnic_attachments,
        compartment_id=compartment_id,
        instance_id=instance_id,
    ).data

    if not vnic_attachments:
        raise Exception("未找到该实例的 VNIC 网卡。")

    # Select the primary VNIC (nic_index == 0), falling back to first if none found.
    primary_vnic = next(
        (v for v in vnic_attachments if v.nic_index == 0),
        vnic_attachments[0],
    )

    private_ips = network_client.list_private_ips(vnic_id=primary_vnic.vnic_id).data

    if not private_ips:
        raise Exception("VNIC 无私有 IP，实例配置异常。")

    return next((ip for ip in private_ips if ip.is_primary), private_ips[0])


def get_current_public_ip(network_client, private_ip_id: str) -> Optional[object]:
    """Return the public IP bound to the given private IP, or None if unbound."""
    try:
        details = oci.core.models.GetPublicIpByPrivateIpIdDetails(
            private_ip_id=private_ip_id
        )
        return network_client.get_public_ip_by_private_ip_id(
            get_public_ip_by_private_ip_id_details=details
        ).data
    except oci.exceptions.ServiceError as e:
        if e.status == 404:
            return None
        raise


def rotate_public_ip(
    network_client,
    compartment_id: str,
    private_ip_id: str,
    current_public_ip,
    dry_run: bool = False,
) -> str:
    """
    Rotate the public IP attached to private_ip_id.

    Strategy: create the new IP first, then delete the old one.
    If creation fails, call sys.exit(1) to avoid leaving the instance
    without a public IP.

    Returns the new IP address string, or the dry-run sentinel.
    """
    if dry_run:
        print("[dry-run] 将执行 IP 轮换，但跳过所有 OCI 写操作。")
        return "[dry-run] 跳过 IP 轮换"

    # Step 1: Create the new reserved public IP bound to the private IP.
    print("[*] 正在向 OCI 申请新的保留公网 IP...")
    try:
        create_details = oci.core.models.CreatePublicIpDetails(
            compartment_id=compartment_id,
            lifetime="RESERVED",
            private_ip_id=private_ip_id,
            display_name="Auto-Rotated-IP",
        )
        new_public_ip = network_client.create_public_ip(
            create_public_ip_details=create_details
        ).data
    except oci.exceptions.ServiceError as e:
        raise RotationError(
            f"新 IP 申请失败，中止轮换以保留现有连接。原因: {e.message}"
        ) from e

    print(f"[+] 新公网 IP 已申请: {new_public_ip.ip_address}")

    # Step 2: Clean up the old IP after the new one is live.
    if current_public_ip:
        if current_public_ip.lifetime == "RESERVED":
            print(
                f"[*] 正在解绑并释放旧保留 IP: {current_public_ip.ip_address}"
            )
            try:
                update_details = oci.core.models.UpdatePublicIpDetails(private_ip_id="")
                network_client.update_public_ip(
                    public_ip_id=current_public_ip.id,
                    update_public_ip_details=update_details,
                )
                network_client.delete_public_ip(
                    public_ip_id=current_public_ip.id
                )
                _wait_until_terminated(network_client, current_public_ip.id)
            except oci.exceptions.ServiceError as e:
                print(
                    f"[!] 旧 IP 清理失败（新 IP 已生效，不影响连接）: {e.message}"
                )
        elif current_public_ip.lifetime == "EPHEMERAL":
            print("[*] 旧临时 IP (EPHEMERAL) 已被新保留 IP 顶替，自动释放。")

    return new_public_ip.ip_address
