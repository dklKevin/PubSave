import logging

from src.logging_config import setup_logging


class TestSetupLogging:
    def teardown_method(self):
        root = logging.getLogger()
        root.handlers.clear()
        root.setLevel(logging.WARNING)

    def test_configures_root_logger_level(self):
        setup_logging("DEBUG")
        assert logging.getLogger().level == logging.DEBUG

    def test_defaults_to_info_on_invalid_level(self):
        setup_logging("NONSENSE")
        assert logging.getLogger().level == logging.INFO

    def test_suppresses_uvicorn_access(self):
        setup_logging("DEBUG")
        assert logging.getLogger("uvicorn.access").level == logging.WARNING

    def test_clears_existing_handlers(self):
        root = logging.getLogger()
        root.addHandler(logging.StreamHandler())
        root.addHandler(logging.StreamHandler())
        assert len(root.handlers) >= 2

        setup_logging("INFO")
        assert len(root.handlers) == 1
