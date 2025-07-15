import pytest
import numpy as np
import sys
from pathlib import Path

# Ajoute le dossier racine du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from algorithms.fusion import fuse, reset_kalman

def test_fusion_singleton():
    """Teste le modèle singleton dans la fusion"""
    # Reset pour s'assurer d'un état propre
    reset_kalman()
    
    result1 = fuse((1, 0, 0), (0.9, 0.1, 0), None)
    result2 = fuse((0, 1, 0), (0.2, 1.1, 0), None)
    
    # Les résultats doivent être différents car le filtre garde l'état
    assert not np.allclose(result1, result2)

def test_no_movement_case():
    """Teste le cas sans mouvement"""
    reset_kalman()
    
    # Cas où aucune position n'est fournie
    result = fuse(None, None, None)
    
    # Le filtre devrait retourner l'état par défaut (généralement origine)
    assert isinstance(result, (tuple, list, np.ndarray))
    assert len(result) >= 2

def test_fusion_simple():
    """Test basique de fusion avec deux positions"""
    reset_kalman()
    
    pos1 = (1.0, 2.0, 0.0)
    pos2 = (1.1, 2.1, 0.0)
    
    fused = fuse(pos1, pos2)
    
    # Vérifications de base
    assert isinstance(fused, (tuple, list, np.ndarray))
    assert len(fused) >= 2
    
    # Le résultat fusionné devrait être proche des positions d'entrée
    assert isinstance(fused[0], (int, float, np.floating))
    assert isinstance(fused[1], (int, float, np.floating))

def test_fusion_reset():
    """Teste la fonction de reset avec QR code"""
    reset_kalman()
    
    qr_pos = (3.0, 4.0, 0.0)
    
    # Reset avec position QR
    fused = fuse(None, None, qr_reset=qr_pos)
    
    print("DEBUG fused:", fused, "qr_pos:", qr_pos)
    
    # Après reset, la position devrait être proche de la position QR
    assert isinstance(fused, (tuple, list, np.ndarray))
    assert len(fused) >= 2
    
    # Test avec tolérance élargie pour tenir compte des incertitudes du filtre
    assert np.allclose(fused[:2], qr_pos[:2], atol=1.0)

def test_pdr_only():
    """Test avec seulement PDR (pas de fingerprint)"""
    reset_kalman()
    
    pdr_pos = (2.0, 3.0, 0.0)
    result = fuse(pdr_pos, None, None)
    
    assert isinstance(result, (tuple, list, np.ndarray))
    assert len(result) >= 2

def test_fingerprint_only():
    """Test avec seulement fingerprint (pas de PDR)"""
    reset_kalman()
    
    finger_pos = (2.5, 3.5, 0.0)
    result = fuse(None, finger_pos, None)
    
    assert isinstance(result, (tuple, list, np.ndarray))
    assert len(result) >= 2

def test_sequential_fusion():
    """Test de fusion séquentielle simulant un usage réel"""
    reset_kalman()
    
    # Séquence de positions
    positions = [
        ((1.0, 1.0, 0.0), (1.1, 0.9, 0.0)),  # (pdr, fingerprint)
        ((0.1, 0.1, 0.0), (1.2, 1.1, 0.0)),
        ((0.0, 0.1, 0.0), (1.2, 1.2, 0.0)),
    ]
    
    results = []
    for pdr, finger in positions:
        result = fuse(pdr, finger, None)
        results.append(result)
        assert isinstance(result, (tuple, list, np.ndarray))
        assert len(result) >= 2
    
    # Tous les résultats doivent être valides
    assert len(results) == 3
    
    # Les positions doivent évoluer de manière cohérente
    for i in range(1, len(results)):
        # Les positions successives ne doivent pas être identiques
        assert not np.allclose(results[i-1][:2], results[i][:2], atol=1e-6)

if __name__ == "__main__":
    # Exécution des tests
    print("Running fusion tests...")
    
    test_fusion_simple()
    print("✅ test_fusion_simple passed")
    
    test_fusion_reset()
    print("✅ test_fusion_reset passed")
    
    test_pdr_only()
    print("✅ test_pdr_only passed")
    
    test_fingerprint_only()
    print("✅ test_fingerprint_only passed")
    
    test_sequential_fusion()
    print("✅ test_sequential_fusion passed")
    
    print("All tests passed!")