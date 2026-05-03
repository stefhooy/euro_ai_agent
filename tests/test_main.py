def test_main_module_imports():
    """Smoke test: main.py imports without errors."""
    import main
    assert hasattr(main, "main")


def test_main_function_is_callable():
    import main
    assert callable(main.main)
