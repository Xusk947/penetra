"""Reconnaissance agent entry point."""

from __future__ import annotations

from agents.common.config import Settings
from agents.recon.graph import build_graph
from tools.recon.nmap import NmapTool

_settings = Settings()
graph = build_graph(NmapTool(mock=_settings.nmap_mock))
