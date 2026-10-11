"""The portal serves a landing page and every package UI it mounts."""

import portal
import pytest
from fastapi.testclient import TestClient
from portal import MOUNTED_UIS

client = TestClient(portal.app)


def test_package_exports_app_and_mounted_uis() -> None:
    assert set(portal.__all__) == {"MOUNTED_UIS", "MountedUi", "app"}


def test_landing_page_links_every_mounted_ui_under_its_role() -> None:
    response = client.get("/")

    assert response.status_code == 200
    for ui in MOUNTED_UIS:
        assert f'<a href="{ui.path}">{ui.title}</a>' in response.text
        assert f"<h2>{ui.role}</h2>" in response.text


def test_landing_page_groups_uis_sharing_a_role_into_one_section() -> None:
    roles = {ui.role for ui in MOUNTED_UIS}

    assert client.get("/").text.count("<section>") == len(roles)


@pytest.mark.parametrize("path", [ui.path for ui in MOUNTED_UIS])
def test_each_mounted_ui_is_served(path: str) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_unknown_path_is_not_found() -> None:
    assert client.get("/no-such-ui").status_code == 404
