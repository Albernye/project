import json
from pathlib import Path
import pytest
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)

from scripts.utils import (cfg, get_logger)
from scripts.update_live import update_qr


logger = get_logger(__name__)


class FakeLogger:
    def info(self, msg):
        logger.info(msg)

    def warning(self, msg):
        logger.warning(msg)

    def error(self, msg):
        logger.error(msg)

@pytest.fixture(autouse=True)
def temp_qr_events(tmp_path, monkeypatch):
    fake = tmp_path / "qr_events.json"
    fake.write_text("[]")
    monkeypatch.setenv("QR_EVENTS", str(fake))
    # ou si cfg.QR_EVENTS est défini directement :
    monkeypatch.setattr(cfg, "QR_EVENTS", str(fake))
    yield


def test_update_qr_creates_event(tmp_path, monkeypatch):
    qr_file = tmp_path / "events.json"
    qr_file.write_text("[]")
    monkeypatch.setattr(cfg, "QR_EVENTS", str(qr_file))
    monkeypatch.setattr(cfg, "DEFAULT_POSXY", (0.0, 0.0))
    update_qr("2-01", logger=FakeLogger())
    data = json.loads(qr_file.read_text())
    assert len(data) == 1
    assert data[0]["position"] == [0.0, 0.0]

def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    logger = logging.getLogger("test_qr_reset")

    # Simulez plusieurs scans de la même salle
    for i in range(3):
        logger.info(f"=== Exécution update_qr, itération {i+1} ===")
        update_qr("2-01", logger)

if __name__ == "__main__":
    main()


