import pytest
from unittest.mock import MagicMock, patch
from rotator import get_primary_private_ip, rotate_public_ip, get_current_public_ip


def _make_vnic(vnic_id="vnic-1", nic_index=0):
    v = MagicMock()
    v.vnic_id = vnic_id
    v.nic_index = nic_index
    return v


def _make_private_ip(ip_id="pip-1", is_primary=True):
    p = MagicMock()
    p.id = ip_id
    p.is_primary = is_primary
    return p


def _make_public_ip(ip_id="pubip-1", addr="1.2.3.4", lifetime="RESERVED"):
    pub = MagicMock()
    pub.id = ip_id
    pub.ip_address = addr
    pub.lifetime = lifetime
    return pub


# ---------------------------------------------------------------------------
# get_primary_private_ip tests — mock at the pagination layer
# ---------------------------------------------------------------------------

def test_get_primary_private_ip_selects_primary_vnic():
    compute_client = MagicMock()
    network_client = MagicMock()
    vnic_secondary = _make_vnic("vnic-2", nic_index=1)
    vnic_primary = _make_vnic("vnic-1", nic_index=0)
    pip = _make_private_ip()
    network_client.list_private_ips.return_value.data = [pip]

    with patch("oci.pagination.list_call_get_all_results") as mock_paginate:
        mock_paginate.return_value.data = [vnic_secondary, vnic_primary]
        result = get_primary_private_ip(compute_client, network_client, "cid", "iid")

    assert result.id == "pip-1"


def test_get_primary_private_ip_raises_when_no_vnic():
    compute_client = MagicMock()
    network_client = MagicMock()

    with patch("oci.pagination.list_call_get_all_results") as mock_paginate:
        mock_paginate.return_value.data = []
        with pytest.raises(Exception, match="未找到"):
            get_primary_private_ip(compute_client, network_client, "cid", "iid")


def test_get_primary_private_ip_raises_when_no_private_ip():
    compute_client = MagicMock()
    network_client = MagicMock()
    network_client.list_private_ips.return_value.data = []

    with patch("oci.pagination.list_call_get_all_results") as mock_paginate:
        mock_paginate.return_value.data = [_make_vnic()]
        with pytest.raises(Exception, match="无私有 IP"):
            get_primary_private_ip(compute_client, network_client, "cid", "iid")


# ---------------------------------------------------------------------------
# rotate_public_ip tests
# ---------------------------------------------------------------------------

def test_rotate_dry_run_skips_oci_calls():
    network_client = MagicMock()
    current_pub = _make_public_ip()
    result = rotate_public_ip(network_client, "cid", "pip-1", current_pub, dry_run=True)
    assert result == "[dry-run] 跳过 IP 轮换"
    network_client.create_public_ip.assert_not_called()
    network_client.delete_public_ip.assert_not_called()


def test_rotate_creates_before_deletes():
    network_client = MagicMock()
    new_pub = _make_public_ip(ip_id="new-1", addr="5.6.7.8")
    network_client.create_public_ip.return_value.data = new_pub
    old_pub = _make_public_ip(ip_id="old-1", addr="1.2.3.4", lifetime="RESERVED")

    with patch("rotator._wait_until_terminated") as mock_wait:
        result = rotate_public_ip(network_client, "cid", "pip-1", old_pub, dry_run=False)

    assert len(network_client.create_public_ip.call_args_list) == 1
    assert len(network_client.update_public_ip.call_args_list) == 1
    assert len(network_client.delete_public_ip.call_args_list) == 1
    assert result == "5.6.7.8"

    # Verify create happened before delete (and update happened before delete).
    all_call_names = [call[0] for call in network_client.mock_calls]
    create_idx = next(i for i, name in enumerate(all_call_names) if name == "create_public_ip")
    update_idx = next(i for i, name in enumerate(all_call_names) if name == "update_public_ip")
    delete_idx = next(i for i, name in enumerate(all_call_names) if name == "delete_public_ip")
    assert create_idx < delete_idx, "create_public_ip must be called before delete_public_ip"
    assert update_idx < delete_idx, "update_public_ip (unbind) must be called before delete_public_ip"
