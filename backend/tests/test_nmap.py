"""Tests for the Nmap scanner policy and allowlist."""

from __future__ import annotations

import pytest

from tests.helpers import EXAMPLE_PRIVATE_IP, LOOPBACK_IP
from tools.recon.nmap import NmapTool


def test_nmap_scan_respects_allowlist() -> None:
    """Nmap must refuse targets outside the configured allowlist."""
    tool = NmapTool(mock=True, allowed_targets=[LOOPBACK_IP])

    result = tool.scan(LOOPBACK_IP)
    assert result.target == LOOPBACK_IP

    with pytest.raises(ValueError, match="not in the scope allowlist"):
        tool.scan(EXAMPLE_PRIVATE_IP)


def test_nmap_policies_build_different_commands() -> None:
    """Each policy should produce a different command shape."""
    safe_tool = NmapTool(mock=True, policy="safe")
    assert "--top-ports" in safe_tool._build_command(LOOPBACK_IP)

    standard_tool = NmapTool(mock=True, policy="standard")
    assert "-sV" in standard_tool._build_command(LOOPBACK_IP)

    aggressive_tool = NmapTool(mock=True, policy="aggressive")
    assert "-A" in aggressive_tool._build_command(LOOPBACK_IP)
