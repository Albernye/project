import pandas as pd
import pytest
from services.utils import config as cfg
from services.update_live import update_localization_files
class DummyLogger:
    def info(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def exception(self, *args, **kwargs): pass

@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch, tmp_path):
    # Temporary directory for all
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))

    # Patch the path of cfg
    monkeypatch.setattr(cfg, "RECORDINGS_DIR", tmp_path)
    monkeypatch.setattr(cfg, "PROCESSED_DIR", tmp_path / "data" / "processed")

    # Simulate calls
    calls = {"pdr": 0, "fp": 0, "qr": 0}
    monkeypatch.setattr("services.update_live.update_pdr", lambda room, logger: calls.__setitem__("pdr", calls["pdr"]+1))
    # monkeypatch.setattr("services.update_live.update_fp",  lambda room, logger: calls.__setitem__("fp",  calls["fp"]+1))
    monkeypatch.setattr("services.update_live.update_qr",  lambda room, logger: calls.__setitem__("qr", calls["qr"]+1))
    return calls

def test_update_localization(tmp_path, patch_dependencies):
    # 1) Fake dataframe
    df = pd.DataFrame({"x": [1, 2, 3]})

    # 2) Create simulated fingerprint file
    room = "2-01"
    folder_name = "2-01"
    (fp_path := tmp_path / folder_name / "latest.csv").parent.mkdir(parents=True, exist_ok=True)
    fp_path.touch()

    # 3) Call
    update_localization_files(df, folder_name, room)

    # 4) Check calls
    calls = patch_dependencies
    assert calls["pdr"] == 1, "update_pdr was not called"
    # assert calls["fp"]  == 1, "update_fp was not called"
    assert calls["qr"]  == 1, "update_qr was not called"

    # 5) Check that the CSV file was written
    processed = tmp_path / "data" / "processed" / f"room_{room}_processed.csv"
    assert processed.exists(), f"{processed} does not exist"
    content = processed.read_text()
    assert "x" in content, "The CSV does not contain the DataFrame data"
