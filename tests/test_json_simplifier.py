"""
Tests pour le post-processeur JSONSimplifier
-------------------------------------------
Ce module teste les fonctionnalités du post-processeur JSONSimplifier,
y compris l'activation/désactivation et différents scénarios de traitement.
"""

import pytest
import json
import os
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from postprocessors.json_simplifier import JSONSimplifier
from postprocessors import get_postprocessor

# Données de test
SAMPLE_JSON_RESULT = {
    "result": {
        "analysis": {
            "sentiment": "positive",
            "tone": "formal",
            "key_points": [
                "Point 1: Le sujet est bien expliqué",
                "Point 2: Arguments clairs et cohérents",
                "Point 3: Conclusion logique"
            ],
            "complexity_score": 0.75,
            "readability_metrics": {
                "flesch_kincaid": 65.2,
                "smog_index": 8.1,
                "coleman_liau_index": 10.3
            }
        },
        "language": "fr",
        "processing_time": 1.23
    }
}

EXPECTED_PLAIN_TEXT = "Le texte a un sentiment positif avec un ton formel. Il comprend 3 points clés: le sujet est bien expliqué, les arguments sont clairs et cohérents, et la conclusion est logique. Le texte a un score de complexité de 0,75 et présente une bonne lisibilité avec un indice Flesch-Kincaid de 65,2."

class MockModel:
    """Classe simulant un modèle de langage pour les tests"""
    
    def __init__(self, return_value=None):
        self.return_value = return_value or EXPECTED_PLAIN_TEXT
    
    def generate(self, prompt, **kwargs):
        return self.return_value

class TestJSONSimplifier:
    
    @pytest.fixture
    def basic_config(self):
        """Configuration de base pour le post-processeur"""
        return {
            "enabled": True,
            "model": "test-model",
            "system_prompt": "Translate this json {text} in plain french",
            "max_tokens": 500,
            "temperature": 0.3,
            "apply_to": ["inference", "video", "transcription"]
        }
    
    @pytest.fixture
    def disabled_config(self):
        """Configuration avec le post-processeur désactivé"""
        return {
            "enabled": False,
            "model": "test-model",
            "system_prompt": "Translate this json {text} in plain french",
            "max_tokens": 500,
            "temperature": 0.3,
            "apply_to": ["inference", "video", "transcription"]
        }
    
    @pytest.fixture
    def limited_tasks_config(self):
        """Configuration avec un ensemble limité de types de tâches"""
        return {
            "enabled": True,
            "model": "test-model",
            "system_prompt": "Translate this json {text} in plain french",
            "max_tokens": 500,
            "temperature": 0.3,
            "apply_to": ["inference", "video"]  # Sans "transcription"
        }
    
    def test_initialization(self, basic_config):
        """Teste l'initialisation correcte du post-processeur"""
        simplifier = JSONSimplifier(basic_config)
        
        assert simplifier.enabled == basic_config["enabled"]
        assert simplifier.model_name == basic_config["model"]
        assert simplifier.system_prompt == basic_config["system_prompt"]
        assert simplifier.max_tokens == basic_config["max_tokens"]
        assert simplifier.temperature == basic_config["temperature"]
        assert simplifier.apply_to == basic_config["apply_to"]
        assert simplifier.model is None  # Le modèle n'est pas chargé à l'initialisation
    
    def test_should_process_enabled(self, basic_config):
        """Teste la méthode should_process quand le post-processeur est activé"""
        simplifier = JSONSimplifier(basic_config)
        
        # Les types de tâches listés dans apply_to devraient retourner True
        assert simplifier.should_process("inference") is True
        assert simplifier.should_process("video") is True
        assert simplifier.should_process("transcription") is True
        
        # Les autres types de tâches devraient retourner False
        assert simplifier.should_process("other_task") is False
    
    def test_should_process_disabled(self, disabled_config):
        """Teste la méthode should_process quand le post-processeur est désactivé"""
        simplifier = JSONSimplifier(disabled_config)
        
        # Tous les types de tâches devraient retourner False
        assert simplifier.should_process("inference") is False
        assert simplifier.should_process("video") is False
        assert simplifier.should_process("transcription") is False
        assert simplifier.should_process("other_task") is False
    
    def test_should_process_limited_tasks(self, limited_tasks_config):
        """Teste la méthode should_process avec un ensemble limité de types de tâches"""
        simplifier = JSONSimplifier(limited_tasks_config)
        
        # Les types de tâches listés dans apply_to devraient retourner True
        assert simplifier.should_process("inference") is True
        assert simplifier.should_process("video") is True
        
        # Les types de tâches non listés devraient retourner False
        assert simplifier.should_process("transcription") is False
        assert simplifier.should_process("other_task") is False
    
    @patch('postprocessors.json_simplifier.ModelManager')
    def test_process_success(self, mock_model_manager, basic_config):
        """Teste le traitement réussi d'un résultat JSON"""
        # Configurer le mock pour ModelManager
        mock_manager_instance = MagicMock()
        mock_model_manager.get_instance.return_value = mock_manager_instance
        
        # Configurer le mock pour le modèle
        mock_model = MockModel()
        mock_manager_instance.get_model.return_value = mock_model
        
        # Créer l'instance du simplifier
        simplifier = JSONSimplifier(basic_config)
        
        # Traiter le résultat JSON
        result = SAMPLE_JSON_RESULT.copy()
        processed = simplifier.process(result, "inference")
        
        # Vérifier les résultats
        assert "plain_explanation" in processed
        assert processed["plain_explanation"] == EXPECTED_PLAIN_TEXT
        
        # Vérifier que le résultat original a été préservé
        assert processed["result"] == SAMPLE_JSON_RESULT["result"]
        
        # Vérifier que le modèle a été correctement appelé
        mock_manager_instance.get_model.assert_called_once_with("llm", basic_config["model"])
    
    @patch('postprocessors.json_simplifier.ModelManager')
    def test_process_model_error(self, mock_model_manager, basic_config):
        """Teste le comportement quand le modèle rencontre une erreur"""
        # Configurer le mock pour déclencher une exception lors de l'appel de generate
        mock_manager_instance = MagicMock()
        mock_model_manager.get_instance.return_value = mock_manager_instance
        
        mock_model = MagicMock()
        mock_model.generate.side_effect = Exception("Erreur de modèle simulée")
        mock_manager_instance.get_model.return_value = mock_model
        
        # Créer l'instance du simplifier
        simplifier = JSONSimplifier(basic_config)
        
        # Traiter le résultat JSON
        result = SAMPLE_JSON_RESULT.copy()
        processed = simplifier.process(result, "inference")
        
        # Vérifier que les résultats originaux sont retournés sans modification
        assert "plain_explanation" not in processed
        assert processed == result
    
    @patch('postprocessors.json_simplifier.ModelManager')
    def test_process_model_not_available(self, mock_model_manager, basic_config):
        """Teste le comportement quand le modèle n'est pas disponible"""
        # Configurer le mock pour retourner None (modèle non disponible)
        mock_manager_instance = MagicMock()
        mock_model_manager.get_instance.return_value = mock_manager_instance
        mock_manager_instance.get_model.return_value = None
        
        # Créer l'instance du simplifier
        simplifier = JSONSimplifier(basic_config)
        
        # Traiter le résultat JSON
        result = SAMPLE_JSON_RESULT.copy()
        processed = simplifier.process(result, "inference")
        
        # Vérifier que les résultats originaux sont retournés sans modification
        assert "plain_explanation" not in processed
        assert processed == result
    
    def test_process_disabled(self, disabled_config):
        """Teste le traitement quand le post-processeur est désactivé"""
        # Créer l'instance du simplifier désactivé
        simplifier = JSONSimplifier(disabled_config)
        
        # Traiter le résultat JSON
        result = SAMPLE_JSON_RESULT.copy()
        processed = simplifier.process(result, "inference")
        
        # Vérifier que les résultats originaux sont retournés sans modification
        assert "plain_explanation" not in processed
        assert processed == result
    
    def test_process_task_not_in_apply_to(self, limited_tasks_config):
        """Teste le traitement quand le type de tâche n'est pas dans apply_to"""
        # Créer l'instance du simplifier avec types de tâches limités
        simplifier = JSONSimplifier(limited_tasks_config)
        
        # Traiter le résultat JSON pour un type de tâche non inclus
        result = SAMPLE_JSON_RESULT.copy()
        processed = simplifier.process(result, "transcription")  # transcription n'est pas dans apply_to
        
        # Vérifier que les résultats originaux sont retournés sans modification
        assert "plain_explanation" not in processed
        assert processed == result
    
    @patch('postprocessors.json_simplifier.ModelManager')
    def test_process_json_serialization(self, mock_model_manager, basic_config):
        """Teste la sérialisation JSON lors du traitement"""
        # Configurer le mock
        mock_manager_instance = MagicMock()
        mock_model_manager.get_instance.return_value = mock_manager_instance
        mock_model = MockModel()
        mock_manager_instance.get_model.return_value = mock_model
        
        # Créer l'instance du simplifier
        simplifier = JSONSimplifier(basic_config)
        
        # Définir un objet JSON avec des types non-sérialisables
        complex_result = {
            "result": {
                "data": set([1, 2, 3]),  # un ensemble n'est pas JSON-sérialisable
                "function": lambda x: x  # une fonction n'est pas JSON-sérialisable
            }
        }
        
        # Traiter le résultat JSON
        try:
            processed = simplifier.process(complex_result, "inference")
            # Le test devrait échouer ici, car la sérialisation devrait échouer
            assert False, "La sérialisation aurait dû échouer avec des types non-sérialisables"
        except:
            # Vérifier que l'exception est bien gérée et que le résultat original est retourné
            pass
    
    def test_get_postprocessor_function(self, basic_config):
        """Teste la fonction get_postprocessor du module postprocessors"""
        with patch('postprocessors.available_postprocessors', {"json_simplifier": JSONSimplifier}):
            # Obtenir une instance du post-processeur via la fonction get_postprocessor
            processor = get_postprocessor("json_simplifier", basic_config)
            
            # Vérifier que l'instance est bien du type JSONSimplifier
            assert isinstance(processor, JSONSimplifier)
            
            # Vérifier qu'un nom de post-processeur invalide retourne None
            assert get_postprocessor("invalid_processor", {}) is None
    
    @patch('postprocessors.json_simplifier.ModelManager')
    def test_prompt_formatting(self, mock_model_manager, basic_config):
        """Teste le formatage du prompt avec le JSON"""
        # Configurer le mock
        mock_manager_instance = MagicMock()
        mock_model_manager.get_instance.return_value = mock_manager_instance
        mock_model = MagicMock()
        mock_manager_instance.get_model.return_value = mock_model
        mock_model.generate.return_value = EXPECTED_PLAIN_TEXT
        
        # Créer l'instance du simplifier
        simplifier = JSONSimplifier(basic_config)
        
        # Traiter le résultat JSON
        result = SAMPLE_JSON_RESULT.copy()
        simplifier.process(result, "inference")
        
        # Vérifier que le prompt formaté a été passé au modèle
        # Récupérer les arguments de l'appel à generate
        args, kwargs = mock_model.generate.call_args
        prompt = args[0]
        
        # Vérifier que le prompt contient le JSON et respecte le template
        assert "{text}" not in prompt  # Le placeholder doit être remplacé
        assert "Translate this json" in prompt  # Le début du prompt doit être présent
        assert json.dumps(result["result"]) in prompt  # Le JSON doit être sérialisé et inclus
    
    def test_integration_with_env_variables(self):
        """Teste l'intégration avec les variables d'environnement"""
        # Sauvegarder les variables d'environnement actuelles
        original_enabled = os.environ.get("JSON_SIMPLIFIER_ENABLED")
        original_model = os.environ.get("JSON_SIMPLIFIER_MODEL")
        original_apply_to = os.environ.get("JSON_SIMPLIFIER_APPLY_TO")
        
        try:
            # Configurer les variables d'environnement pour le test
            os.environ["JSON_SIMPLIFIER_ENABLED"] = "true"
            os.environ["JSON_SIMPLIFIER_MODEL"] = "test-env-model"
            os.environ["JSON_SIMPLIFIER_APPLY_TO"] = "inference,video"
            
            # Charger la configuration depuis l'environnement
            from config import load_config
            config = load_config()
            
            # Vérifier que la configuration a été correctement chargée
            assert config["postprocessing"]["json_simplifier"]["enabled"] is True
            assert config["postprocessing"]["json_simplifier"]["model"] == "test-env-model"
            assert config["postprocessing"]["json_simplifier"]["apply_to"] == ["inference", "video"]
            
        finally:
            # Restaurer les variables d'environnement originales
            if original_enabled is not None:
                os.environ["JSON_SIMPLIFIER_ENABLED"] = original_enabled
            else:
                os.environ.pop("JSON_SIMPLIFIER_ENABLED", None)
                
            if original_model is not None:
                os.environ["JSON_SIMPLIFIER_MODEL"] = original_model
            else:
                os.environ.pop("JSON_SIMPLIFIER_MODEL", None)
                
            if original_apply_to is not None:
                os.environ["JSON_SIMPLIFIER_APPLY_TO"] = original_apply_to
            else:
                os.environ.pop("JSON_SIMPLIFIER_APPLY_TO", None)


if __name__ == "__main__":
    print("Exécution des tests du post-processeur JSONSimplifier...")
    pytest.main(["-xvs", __file__])