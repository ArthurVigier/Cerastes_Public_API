#!/usr/bin/env python3
"""
Script pour exécuter les tests de l'API d'inférence multi-session.
Ce script permet d'exécuter tous les tests ou des catégories spécifiques.
"""
# Au début de votre fichier run_tests.py, ajoutez:
import os
os.environ["SAMPLE_VIDEO_PATH"] = "tests/fixtures/sample_video.mp4"
import argparse
import subprocess
import sys
import time

def parse_args():
    parser = argparse.ArgumentParser(description="Exécute les tests de l'API d'inférence multi-session")
    
    parser.add_argument("--auth", action="store_true", help="Exécuter les tests d'authentification")
    parser.add_argument("--inference", action="store_true", help="Exécuter les tests d'inférence")
    parser.add_argument("--limits", action="store_true", help="Exécuter les tests des limites d'utilisation")
    parser.add_argument("--video", action="store_true", help="Exécuter les tests d'analyse vidéo")
    parser.add_argument("--transcription", action="store_true", help="Exécuter les tests de transcription")
    parser.add_argument("--task", action="store_true", help="Exécuter les tests de gestion des tâches")
    parser.add_argument("--health", action="store_true", help="Exécuter les tests de santé")
    parser.add_argument("--subscription", action="store_true", help="Exécuter les tests d'abonnement")
    parser.add_argument("--integration", action="store_true", help="Exécuter les tests d'intégration")
    parser.add_argument("--json-simplifier", action="store_true", help="Exécuter les tests du JSONSimplifier")
    parser.add_argument("--prompt-manager", action="store_true", help="Exécuter les tests du gestionnaire de prompts")
    parser.add_argument("--all", action="store_true", help="Exécuter tous les tests")
    parser.add_argument("--api-url", type=str, help="URL de base de l'API", default="http://localhost:8000")
    parser.add_argument("--api-key", type=str, help="Clé API à utiliser pour les tests")
    parser.add_argument("--premium-key", type=str, help="Clé API premium à utiliser pour les tests")
    parser.add_argument("--token", type=str, help="Token JWT à utiliser pour les tests")
    
    return parser.parse_args()

def run_test_file(test_file, api_url=None, api_key=None, premium_key=None, token=None):
    """Exécute un fichier de test spécifique."""
    print(f"\n=== Exécution de {test_file} ===\n")
    
    # Préparer les variables d'environnement
    env = os.environ.copy()
    if api_url:
        env["API_BASE_URL"] = api_url
    if api_key:
        env["TEST_API_KEY"] = api_key
        env["TEST_FREE_API_KEY"] = api_key
    if premium_key:
        env["TEST_PREMIUM_API_KEY"] = premium_key
    if token:
        env["TEST_TOKEN"] = token
    
    # Exécuter le test
    try:
        result = subprocess.run([sys.executable, test_file], env=env, check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"Erreur lors de l'exécution de {test_file}: {e}")
        return False

def main():
    args = parse_args()
    
    # Si aucun test n'est spécifié, exécuter tous les tests
    if not (args.auth or args.inference or args.limits or args.video or 
            args.transcription or args.task or args.health or 
            args.subscription or args.integration or args.json_simplifier or
            args.prompt_manager or args.all):
        args.all = True
    
    # Déterminer quels tests exécuter
    tests_to_run = []
    if args.auth or args.all:
        tests_to_run.append("test_auth.py")
    if args.inference or args.all:
        tests_to_run.append("test_inference.py")
    if args.limits or args.all:
        tests_to_run.append("test_limits.py")
    if args.video or args.all:
        tests_to_run.append("test_video.py")
    if args.transcription or args.all:
        tests_to_run.append("test_transcription.py")
    if args.task or args.all:
        tests_to_run.append("test_task.py")
    if args.health or args.all:
        tests_to_run.append("test_health.py")
    if args.subscription or args.all:
        tests_to_run.append("test_subscription.py")
    if args.integration or args.all:
        tests_to_run.append("test_integration.py")
    if args.json_simplifier or args.all:
        tests_to_run.append("test_json_simplifier.py")
    if args.prompt_manager or args.all:
        tests_to_run.append("test_prompt_manager.py")
    
    # Afficher les paramètres
    print(f"URL de l'API: {args.api_url}")
    print(f"Tests à exécuter: {', '.join(tests_to_run)}")
    
    # Exécuter les tests
    success = True
    start_time = time.time()
    
    for test_file in tests_to_run:
        if not run_test_file(test_file, args.api_url, args.api_key, args.premium_key, args.token):
            success = False
    
    # Afficher le résultat global
    execution_time = time.time() - start_time
    print(f"\n=== Résultats des tests ===")
    print(f"Temps d'exécution: {execution_time:.2f} secondes")
    
    if success:
        print("\033[92mTous les tests ont réussi!\033[0m")
        return 0
    else:
        print("\033[91mCertains tests ont échoué.\033[0m")
        return 1

if __name__ == "__main__":
    sys.exit(main())