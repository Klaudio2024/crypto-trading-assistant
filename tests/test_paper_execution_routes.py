import main


def test_manual_paper_signal_route_is_not_public():
    routes = {route.path for route in main.app.routes}

    assert "/api/paper-signal" not in routes
    assert "/api/strategy/paper" in routes


def test_paper_execution_helper_is_internal():
    assert hasattr(main, "_execute_paper_signal")
    assert not hasattr(main, "paper")

from pathlib import Path


def test_dashboard_starts_paper_execution_from_strategy_route():
    dashboard = Path("app/static/index.html").read_text()

    assert "/api/strategy/paper" in dashboard
    assert "/api/paper-signal" not in dashboard
