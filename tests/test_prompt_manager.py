"""
Tests pour le gestionnaire de prompts
------------------------------------
Ce module vérifie les fonctionnalités du gestionnaire de prompts,
notamment le chargement, le formatage et la gestion des placeholders.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from utils.prompt_manager import PromptManager, get_prompt_manager

class TestPromptManager:
    
    @pytest.fixture
    def test_prompts_dir(self):
        """Crée un répertoire temporaire avec des prompts de test."""
        temp_dir = tempfile.mkdtemp()
        prompts_dir = Path(temp_dir) / "prompts"
        prompts_dir.mkdir()
        
        # Créer des fichiers de prompts de test
        with open(prompts_dir / "test1.txt", "w", encoding="utf-8") as f:
            f.write("Voici un prompt avec {placeholder1} et {placeholder2}")
        
        with open(prompts_dir / "test2.txt", "w", encoding="utf-8") as f:
            f.write("Un prompt sans placeholder")
        
        with open(prompts_dir / "test3.txt", "w", encoding="utf-8") as f:
            f.write("Analyse {text} en français")
        
        with open(prompts_dir / "test_multiples.txt", "w", encoding="utf-8") as f:
            f.write("Prompt utilisant {text} plusieurs fois: {text}")
        
        # Ajouter un fichier JSON de collection
        with open(prompts_dir / "prompts.json", "w", encoding="utf-8") as f:
            f.write('''{
                "json_prompt1": "Prompt JSON avec {json_var}",
                "json_prompt2": "Autre prompt JSON avec {text}"
            }''')
        
        yield prompts_dir
        
        # Nettoyer après les tests
        shutil.rmtree(temp_dir)
    
    def test_initialization(self, test_prompts_dir):
        """Teste l'initialisation du gestionnaire de prompts."""
        prompt_manager = PromptManager(prompts_dir=str(test_prompts_dir))
        
        # Vérifier que les prompts ont été chargés
        assert "test1" in prompt_manager.prompts_cache
        assert "test2" in prompt_manager.prompts_cache
        assert "test3" in prompt_manager.prompts_cache
        assert "json_prompt1" in prompt_manager.prompts_cache
        assert "json_prompt2" in prompt_manager.prompts_cache
    
    def test_get_prompt(self, test_prompts_dir):
        """Teste la récupération des prompts bruts."""
        prompt_manager = PromptManager(prompts_dir=str(test_prompts_dir))
        
        # Récupérer des prompts
        assert prompt_manager.get_prompt("test1") == "Voici un prompt avec {placeholder1} et {placeholder2}"
        assert prompt_manager.get_prompt("test2") == "Un prompt sans placeholder"
        assert prompt_manager.get_prompt("nonexistent") is None
    
    def test_get_placeholder_names(self, test_prompts_dir):
        """Teste l'extraction des noms de placeholders."""
        prompt_manager = PromptManager(prompts_dir=str(test_prompts_dir))
        
        # Récupérer les noms de placeholders
        assert set(prompt_manager.get_placeholder_names("test1")) == {"placeholder1", "placeholder2"}
        assert prompt_manager.get_placeholder_names("test2") == []
        assert prompt_manager.get_placeholder_names("test3") == ["text"]
        assert prompt_manager.get_placeholder_names("test_multiples") == ["text"]  # Les doublons ne sont listés qu'une fois
    
    def test_format_prompt(self, test_prompts_dir):
        """Teste le formatage des prompts avec des variables."""
        prompt_manager = PromptManager(prompts_dir=str(test_prompts_dir))
        
        # Formater des prompts avec les variables requises
        formatted = prompt_manager.format_prompt("test1", placeholder1="valeur1", placeholder2="valeur2")
        assert formatted == "Voici un prompt avec valeur1 et valeur2"
        
        # Formater un prompt sans placeholder
        formatted = prompt_manager.format_prompt("test2")
        assert formatted == "Un prompt sans placeholder"
        
        # Formater avec le placeholder standard {text}
        formatted = prompt_manager.format_prompt("test3", text="un texte d'exemple")
        assert formatted == "Analyse un texte d'exemple en français"
        
        # Formater avec des placeholders utilisés plusieurs fois
        formatted = prompt_manager.format_prompt("test_multiples", text="répété")
        assert formatted == "Prompt utilisant répété plusieurs fois: répété"
    
    def test_format_prompt_with_extra_vars(self, test_prompts_dir):
        """Teste le formatage des prompts avec des variables supplémentaires."""
        prompt_manager = PromptManager(prompts_dir=str(test_prompts_dir))
        
        # Variables supplémentaires ignorées
        formatted = prompt_manager.format_prompt("test3", text="exemple", extra_var="ignorée")
        assert formatted == "Analyse exemple en français"
    
    def test_format_prompt_missing_vars(self, test_prompts_dir):
        """Teste le formatage des prompts avec des variables manquantes."""
        prompt_manager = PromptManager(prompts_dir=str(test_prompts_dir))
        
        # Variable manquante
        formatted = prompt_manager.format_prompt("test1", placeholder1="valeur1")
        assert formatted is None
    
    def test_format_prompt_direct(self, test_prompts_dir):
        """Teste le formatage direct des prompts."""
        prompt_manager = PromptManager(prompts_dir=str(test_prompts_dir))
        
        # Formatage direct
        template = "Voici {var1} et {var2}"
        formatted = prompt_manager.format_prompt_direct(template, var1="test1", var2="test2")
        assert formatted == "Voici test1 et test2"
        
        # Formatage direct avec des variables supplémentaires
        formatted = prompt_manager.format_prompt_direct(template, var1="test1", var2="test2", extra="ignoré")
        assert formatted == "Voici test1 et test2"
        
        # Formatage direct avec des variables manquantes
        formatted = prompt_manager.format_prompt_direct(template, var1="test1")
        assert formatted == template  # Devrait retourner le template original
    
    def test_format_prompt_direct_special_chars(self, test_prompts_dir):
        """Teste le formatage direct avec des caractères spéciaux."""
        prompt_manager = PromptManager(prompts_dir=str(test_prompts_dir))
        
        template = "Caractères spéciaux: {chars}"
        formatted = prompt_manager.format_prompt_direct(template, chars="é à ù € \n \t")
        assert formatted == "Caractères spéciaux: é à ù € \n \t"
    
    def test_add_prompt(self, test_prompts_dir):
        """Teste l'ajout et la mise à jour de prompts."""
        prompt_manager = PromptManager(prompts_dir=str(test_prompts_dir))
        
        # Ajouter un nouveau prompt
        prompt_manager.add_prompt("new_prompt", "Nouveau prompt avec {param}")
        assert prompt_manager.get_prompt("new_prompt") == "Nouveau prompt avec {param}"
        
        # Mettre à jour un prompt existant
        prompt_manager.add_prompt("test1", "Prompt mis à jour avec {new_param}")
        assert prompt_manager.get_prompt("test1") == "Prompt mis à jour avec {new_param}"
    
    def test_singleton_instance(self):
        """Teste que get_prompt_manager retourne une instance singleton."""
        manager1 = get_prompt_manager()
        manager2 = get_prompt_manager()
        
        # Vérifier que c'est la même instance
        assert manager1 is manager2
        
        # Ajouter un prompt et vérifier qu'il est disponible dans les deux références
        manager1.add_prompt("singleton_test", "Test du singleton avec {var}")
        assert manager2.get_prompt("singleton_test") == "Test du singleton avec {var}"
    
    def test_standard_placeholders(self, test_prompts_dir):
        """Teste l'utilisation des placeholders standards."""
        prompt_manager = PromptManager(prompts_dir=str(test_prompts_dir))
        
        # Ajouter des prompts avec différents placeholders standards
        standard_placeholders = {
            "text_prompt": "Texte: {text}",
            "input_prompt": "Entrée: {input}",
            "query_prompt": "Requête: {query}",
            "language_prompt": "Langue: {language}",
            "content_prompt": "Contenu: {content}",
            "context_prompt": "Contexte: {context}",
            "question_prompt": "Question: {question}",
            "data_prompt": "Données: {data}",
            "json_prompt": "JSON: {json}",
            "transcript_prompt": "Transcription: {transcript}",
            "multi_prompt": "Multiple: {text} {language} {context}"
        }
        
        for name, template in standard_placeholders.items():
            prompt_manager.add_prompt(name, template)
        
        # Tester chaque placeholder standard
        assert prompt_manager.format_prompt("text_prompt", text="exemple") == "Texte: exemple"
        assert prompt_manager.format_prompt("input_prompt", input="valeur") == "Entrée: valeur"
        assert prompt_manager.format_prompt("query_prompt", query="recherche") == "Requête: recherche"
        assert prompt_manager.format_prompt("language_prompt", language="français") == "Langue: français"
        assert prompt_manager.format_prompt("content_prompt", content="contenu") == "Contenu: contenu"
        assert prompt_manager.format_prompt("context_prompt", context="contexte") == "Contexte: contexte"
        assert prompt_manager.format_prompt("question_prompt", question="pourquoi?") == "Question: pourquoi?"
        assert prompt_manager.format_prompt("data_prompt", data="données") == "Données: données"
        assert prompt_manager.format_prompt("json_prompt", json="{\"key\":\"value\"}") == "JSON: {\"key\":\"value\"}"
        assert prompt_manager.format_prompt("transcript_prompt", transcript="texte") == "Transcription: texte"
        
        # Tester un prompt avec plusieurs placeholders
        formatted = prompt_manager.format_prompt("multi_prompt", text="texte", language="fr", context="ctx")
        assert formatted == "Multiple: texte fr ctx"