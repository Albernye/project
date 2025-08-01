import pandas as pd
import pytest
from pathlib import Path
from scripts.utils import cfg
from scripts.update_live import update_localization_files

class DummyLogger:
    def info(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def exception(self, *args, **kwargs): pass

@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch, tmp_path):
    # Dossier temporaire pour tout
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))

    # Patch les chemins de cfg
    monkeypatch.setattr(cfg, "RECORDINGS_DIR", tmp_path)
    monkeypatch.setattr(cfg, "PROCESSED_DIR", tmp_path / "data" / "processed")

    # Simuler les appels
    calls = {"pdr": 0, "fp": 0, "qr": 0}
    monkeypatch.setattr("scripts.update_live.update_pdr", lambda room, logger: calls.__setitem__("pdr", calls["pdr"]+1))
    monkeypatch.setattr("scripts.update_live.update_fp",  lambda room, logger: calls.__setitem__("fp",  calls["fp"]+1))
    monkeypatch.setattr("scripts.update_live.update_qr",  lambda room, logger: calls.__setitem__("qr", calls["qr"]+1))
    return calls

def test_update_localization(tmp_path, patch_dependencies):
    # 1) DataFrame factice
    df = pd.DataFrame({"x": [1, 2, 3]})

    # 2) Création du fichier fingerprint simulé
    room = "2-01"
    folder_name = "2-01"
    (fp_path := tmp_path / folder_name / "latest.csv").parent.mkdir(parents=True, exist_ok=True)
    fp_path.touch()

    # 3) Appel
    update_localization_files(df, folder_name, room)

    # 4) Vérifier les appels
    calls = patch_dependencies
    assert calls["pdr"] == 1, "update_pdr n'a pas été appelé"
    assert calls["fp"]  == 1, "update_fp n'a pas été appelé"
    assert calls["qr"]  == 1, "update_qr n'a pas été appelé"

    # 5) Vérifier que le fichier CSV a été écrit
    processed = tmp_path / "data" / "processed" / f"room_{room}_processed.csv"
    assert processed.exists(), f"{processed} n'existe pas"
    content = processed.read_text()
    assert "x" in content, "Le CSV ne contient pas les données du DataFrame"
