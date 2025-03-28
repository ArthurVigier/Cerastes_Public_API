"""
Text segmentation utilities for processing large texts.
"""
import logging
import re
from typing import List, Optional, Tuple

# Logging configuration
logger = logging.getLogger("utils.segmentation")

def split_text_into_segments(
    text: str, 
    max_length: int = 2000,
    overlap: int = 200
) -> List[str]:
    """
    Splits text into segments while preserving semantic integrity using
    intelligent boundary detection.
    
    Args:
        text: Text to split
        max_length: Maximum length of each segment
        overlap: Number of characters to overlap between segments
        
    Returns:
        List of text segments
    """
    if not text:
        return []
        
    if len(text) <= max_length:
        return [text]
    
    # Prétraitement: normalisation des sauts de ligne
    text = re.sub(r'\r\n', '\n', text)
    
    segments = []
    start = 0
    
    # Reconnaissance améliorée des limites de phrases
    sentence_boundaries = r'(?<=[.!?;])\s+(?=[A-Z0-9])'
    paragraph_boundaries = r'\n\s*\n'
    section_boundaries = r'(?:^|\n)#+\s+.+?(?:\n|$)|(?:^|\n)\*\*.*?\*\*(?:\n|$)'
    
    while start < len(text):
        # Déterminer la position de fin potentielle
        end_pos = start + max_length
        
        if end_pos >= len(text):
            segments.append(text[start:])
            break
        
        # Trouver le meilleur point de coupure en analysant le contexte
        best_break = find_optimal_break_point(text, start, end_pos)
        
        # Éviter la coupure à l'intérieur des structures comme les citations ou les listes
        if is_inside_structure(text, best_break):
            # Chercher la fin ou le début de la structure
            best_break = adjust_for_structures(text, best_break, start, end_pos)
        
        # Ajouter le segment
        segments.append(text[start:best_break])
        
        # Déplacer le début avec chevauchement
        start = max(start + 1, best_break - overlap)
    
    return segments

def find_optimal_break_point(text: str, start: int, end: int) -> int:
    """
    Trouve le point de coupure optimal en fonction du contexte linguistique.
    """
    # Priorité pour la recherche des points de coupure
    break_hierarchy = [
        # 1. Limites de sections (titres, sous-titres)
        (r'\n#{1,6}\s+', 800),
        
        # 2. Sauts de paragraphe
        (r'\n\s*\n', 700),
        
        # 3. Fin de phrase suivie d'une nouvelle phrase
        (r'(?<=[.!?])\s+(?=[A-Z])', 600),
        
        # 4. Fin de phrase (autres cas)
        (r'(?<=[.!?])\s+', 500),
        
        # 5. Points-virgules et autres séparateurs forts
        (r'(?<=;)\s+', 400),
        
        # 6. Virgules entre clauses
        (r'(?<=,)\s+(?=(?:and|or|but|nor|yet|so|whereas|while|although|though|because|since|unless|until|if|when|where|which|who|whom|whose))', 300),
        
        # 7. Simples virgules
        (r'(?<=,)\s+', 200),
        
        # 8. Sauts de ligne simples
        (r'\n', 100),
    ]
    
    # Partir de la fin et chercher vers le début
    search_area = text[start:end]
    best_break = end
    best_priority = 0
    
    # Rechercher le meilleur point selon la hiérarchie
    for pattern, priority in break_hierarchy:
        matches = list(re.finditer(pattern, search_area))
        if matches:
            # Privilégier les coupures qui sont au moins à mi-chemin
            for match in reversed(matches):
                match_pos = start + match.start()
                # S'assurer que nous sommes au moins à 40% du chemin dans le segment
                min_pos = start + (end - start) * 0.4
                if match_pos >= min_pos and priority > best_priority:
                    best_break = match_pos + len(match.group(0))
                    best_priority = priority
                    break
    
    # Si aucun point de coupure idéal n'a été trouvé, utiliser la position maximum
    return best_break

def is_inside_structure(text: str, position: int) -> bool:
    """
    Vérifie si la position se trouve à l'intérieur d'une structure spéciale
    comme une citation, un bloc de code, une liste, etc.
    """
    # Définir les marqueurs de début et de fin des structures spéciales
    structures = [
        (r'```', r'```'),              # Blocs de code
        (r'~~~', r'~~~'),              # Blocs alternatifs
        (r'`', r'`'),                  # Code inline
        (r'\(', r'\)'),                # Parenthèses
        (r'\[', r'\]'),                # Crochets
        (r'"', r'"'),                  # Citations doubles
        (r"'", r"'"),                  # Citations simples
        (r'<', r'>'),                  # Tags HTML
    ]
    
    # Vérifier pour chaque type de structure
    pre_context = text[:position]
    post_context = text[position:]
    
    for start_marker, end_marker in structures:
        # Compter les occurrences des marqueurs de début et de fin avant la position
        starts = len(re.findall(start_marker, pre_context))
        ends = len(re.findall(end_marker, pre_context))
        
        # Si le nombre de débuts est supérieur au nombre de fins,
        # nous sommes à l'intérieur d'une structure
        if starts > ends:
            return True
    
    return False

def adjust_for_structures(text: str, position: int, min_pos: int, max_pos: int) -> int:
    """
    Ajuste la position pour éviter de couper à l'intérieur des structures spéciales.
    """
    # Chercher la fin de la structure la plus proche
    post_context = text[position:max_pos]
    structure_end_patterns = [r'```', r'~~~', r'`', r'\)', r'\]', r'"', r"'", r'>']
    
    for pattern in structure_end_patterns:
        match = re.search(pattern, post_context)
        if match:
            return position + match.end()
    
    # Si aucune fin de structure n'est trouvée, chercher le début de structure précédent
    pre_context = text[min_pos:position]
    structure_start_patterns = [r'```', r'~~~', r'`', r'\(', r'\[', r'"', r"'", r'<']
    
    for pattern in reversed(structure_start_patterns):
        matches = list(re.finditer(pattern, pre_context))
        if matches:
            return min_pos + matches[-1].start()
    
    # Si aucun ajustement n'est possible, retourner la position d'origine
    return position