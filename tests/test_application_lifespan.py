import main


def test_application_uses_lifespan_instead_of_deprecated_startup_event():
    assert main.app.router.on_startup == []
    assert main.app.router.lifespan_context is main.lifespan
