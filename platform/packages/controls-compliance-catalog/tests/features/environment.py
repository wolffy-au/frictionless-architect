"""behave environment: run the real FastAPI app and a Playwright browser for UI scenarios."""

from __future__ import annotations

import socket
import threading
import time

import uvicorn
from behave.runner import Context
from controls_compliance_catalog.app import app
from playwright.sync_api import sync_playwright


def _free_port_socket() -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    return sock


def before_all(context: Context) -> None:
    sock = _free_port_socket()
    port = sock.getsockname()[1]
    config = uvicorn.Config(app, fd=sock.fileno(), log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)

    context.base_url = f"http://127.0.0.1:{port}"
    context.uvicorn_server = server
    context.uvicorn_thread = thread

    context.playwright = sync_playwright().start()
    context.browser = context.playwright.chromium.launch()


def before_scenario(context: Context, _scenario: object) -> None:
    context.page = context.browser.new_page()


def after_scenario(context: Context, _scenario: object) -> None:
    context.page.close()


def after_all(context: Context) -> None:
    # before_all may have failed partway (e.g. Playwright's browser missing), leaving
    # later attributes unset; guard each teardown so the real failure isn't masked.
    if hasattr(context, "browser"):
        context.browser.close()
    if hasattr(context, "playwright"):
        context.playwright.stop()
    if hasattr(context, "uvicorn_server"):
        context.uvicorn_server.should_exit = True
        context.uvicorn_thread.join(timeout=5)
