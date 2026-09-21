from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "async_harness.py"
spec = importlib.util.spec_from_file_location("async_harness", MODULE_PATH)
harness = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(harness)


def test_direct_notification_is_native_windows_only():
    assert harness.is_windows_host() is (os.name == "nt")


def test_relay_config_reads_token_file_without_copying_secret(tmp_path):
    token_path = tmp_path / "token.txt"
    token_path.write_text("test-secret-token-value\n", encoding="utf-8")
    home = tmp_path / "home"
    config_dir = home / ".config" / "gonglz"
    config_dir.mkdir(parents=True)
    (config_dir / "async-harness.json").write_text(json.dumps({"relay_url": "http://100.64.0.1:18791/notify", "token_file": str(token_path)}), encoding="utf-8")
    with mock.patch.object(Path, "home", return_value=home), mock.patch.dict(os.environ, {"HARNESS_NOTIFY_RELAY_URL": "", "HARNESS_NOTIFY_TOKEN": "", "HARNESS_NOTIFY_TOKEN_FILE": ""}, clear=False):
        assert harness.relay_config() == ("http://100.64.0.1:18791/notify", "test-secret-token-value")


def test_env_token_file_takes_precedence(tmp_path):
    token_path = tmp_path / "token.txt"
    token_path.write_text("env-secret\n", encoding="utf-8")
    with mock.patch.dict(os.environ, {"HARNESS_NOTIFY_RELAY_URL": "http://100.64.0.2:18791/notify", "HARNESS_NOTIFY_TOKEN": "", "HARNESS_NOTIFY_TOKEN_FILE": str(token_path)}, clear=False):
        assert harness.relay_config() == ("http://100.64.0.2:18791/notify", "env-secret")
