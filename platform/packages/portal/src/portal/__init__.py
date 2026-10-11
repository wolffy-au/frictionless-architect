"""Portal: one app that hosts the platform packages' UIs.

Mounts each package's router and owns only page chrome, navigation and the
role landing page — never feature logic (ADR-0020, update 2026-10-11).
"""

from portal.app import MOUNTED_UIS, MountedUi, app

__all__ = ["MOUNTED_UIS", "MountedUi", "app"]
