import os
import pytest
from unittest.mock import patch


def test_load_config_missing_instance_id():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(SystemExit):
            from config import load_config
            import importlib, config
            importlib.reload(config)
            config.load_config()


def test_load_config_returns_expected_keys():
    env = {
        "OCI_INSTANCE_ID": "ocid1.instance.oc1.test",
        "OCI_CONFIG_PROFILE": "DEFAULT",
        "CHECK_PORT": "22",
        "CHECK_TIMEOUT": "5",
    }
    with patch.dict(os.environ, env, clear=True):
        import importlib, config
        importlib.reload(config)
        cfg = config.load_config()
        assert cfg["instance_id"] == "ocid1.instance.oc1.test"
        assert cfg["check_port"] == 22
        assert cfg["check_timeout"] == 5
        assert cfg["config_profile"] == "DEFAULT"
        assert cfg["dry_run"] is False


def test_load_config_invalid_check_port():
    env = {
        "OCI_INSTANCE_ID": "ocid1.instance.oc1.test",
        "CHECK_PORT": "not_a_number",
    }
    with patch.dict(os.environ, env, clear=True):
        import importlib, config
        importlib.reload(config)
        with pytest.raises(SystemExit):
            config.load_config()
