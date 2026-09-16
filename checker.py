import socket
from typing import Optional

import requests


def _check_pingpe(ip: str, timeout: int) -> Optional[bool]:
    """
    Returns True=blocked, False=accessible, None=API unavailable.
    Judges blocked if average loss rate of China nodes > 50%.
    """
    try:
        resp = requests.get(
            "https://ping.pe/api/check",
            params={"host": ip},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        cn_nodes = [v for k, v in data.items() if "china" in k.lower() or "cn" in k.lower()]
        if not cn_nodes:
            return None
        loss_values = [node.get("loss", 0) for node in cn_nodes if isinstance(node, dict)]
        if not loss_values:
            return None
        avg_loss = sum(loss_values) / len(loss_values)
        return avg_loss > 50
    except Exception:
        return None


def _check_ipcheck(ip: str, timeout: int) -> Optional[bool]:
    """
    Returns True=blocked, False=accessible, None=API unavailable.
    Judges blocked when cn_accessible is False.
    """
    try:
        resp = requests.get(
            "https://ipcheck.ing/api/check",
            params={"ip": ip},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        accessible = data.get("cn_accessible")
        if accessible is None:
            return None
        return not accessible
    except Exception:
        return None


def _check_tcp(ip: str, port: int, timeout: int) -> bool:
    """Local TCP probe. Returns True=unreachable (blocked), False=reachable."""
    print(f"[*] Fallback: local TCP probe {ip}:{port}")
    try:
        sock = socket.create_connection((ip, port), timeout=timeout)
        sock.close()
        return False
    except (socket.timeout, ConnectionRefusedError, OSError):
        return True


def is_ip_blocked(ip: str, port: int, timeout: int) -> bool:
    """
    Returns True if the IP is judged blocked in mainland China, False otherwise.

    Voting logic:
    - Both APIs return results: blocked only if both report blocked (>=2 sources).
    - Only one API returns a result: not blocked (requires >=2 sources to confirm).
    - Both APIs unavailable (None): fall back to local TCP probe.
    """
    print(f"[*] Checking CN reachability for IP {ip}...")

    pingpe_result = _check_pingpe(ip, timeout)
    ipcheck_result = _check_ipcheck(ip, timeout)

    results = [r for r in [pingpe_result, ipcheck_result] if r is not None]

    if len(results) == 0:
        print("[!] All third-party APIs unavailable, falling back to local TCP probe")
        return _check_tcp(ip, port, timeout)

    blocked_count = sum(1 for r in results if r is True)

    if len(results) >= 2:
        blocked = blocked_count >= 2
    else:
        # Only one source available — spec requires >=2 sources to confirm blocked.
        blocked = False

    if blocked:
        print(f"[-] Result: IP {ip} is inaccessible in mainland China, triggering rotation.")
    else:
        print(f"[+] Result: IP {ip} is accessible, no rotation needed.")

    return blocked
