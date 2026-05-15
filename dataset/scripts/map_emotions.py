#!/usr/bin/env python3
"""
Script para mapear emociones de GoEmotions (28) a Synapse (9).

Mapeo basado en investigación académica:
- GoEmotions: 28 emociones de Reddit
- Synapse: 9 emociones educativas para programación

Uso:
    python map_emotions.py
"""

import os
import sys
import json
from pathlib import Path
from collections import Counter

# Configurar paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
RAW_DIR = PROJECT_ROOT / "dataset" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "dataset" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Mapeo de emociones GoEmotions (28) → Synapse (9)
# Basado en investigación de taxonomías emocionales educativas
EMOTION_MAPPING = {
    # frustracion: emociones negativas intensas
    "anger": "frustracion",
    "annoyance": "frustracion",
    "disapproval": "frustracion",
    
    # confusion: falta de comprensión
    "confusion": "confusion",
    
    # curiosidad: interés y deseo de aprender
    "curiosity": "curiosidad",
    "interest": "curiosidad",
    "desire": "curiosidad",
    
    # ansiedad: nerviosismo y preocupación
    "nervousness": "ansiedad",
    "fear": "ansiedad",
    
    # motivacion: emociones positivas y energía
    "admiration": "motivacion",
    "approval": "motivacion",
    "excitement": "motivacion",
    "joy": "motivacion",
    "love": "motivacion",
    "optimism": "motivacion",
    "pride": "motivacion",
    "gratitude": "motivacion",
    
    # abrumado: sobrecarga cognitiva
    "surprise": "abrumado",
    "realization": "abrumado",
    
    # desesperado: emociones negativas de derrota
    "sadness": "desesperado",
    "disappointment": "desesperado",
    "grief": "desesperado",
    "remorse": "desesperado",
    "embarrassment": "desesperado",
    
    # neutral: sin carga emocional
    "neutral": "neutral",
    "caring": "neutral",
    
    # Emociones adicionales que pueden aparecer
    "amusement": "motivacion",
    "disgust": "frustracion",
    "relief": "motivacion",
}


def map_emotion(goemotion_label: str) -> str:
    """
    Mapea una emoción de GoEmotions a una emoción de Synapse.
    
    Args:
        goemotion_label: Emoción original de GoEmotions
    
    Returns:
        Emoción mapeada de Synapse
    """
    # Mapeo directo
    if goemotion_label in EMOTION_MAPPING:
        return EMOTION_MAPPING[goemotion_label]
    
    # Si no se encuentra, devolver neutral
    print(f"  ⚠ Emoción no mapeada: {goemotion_label} → neutral")
    return "neutral"


def map_emotions_for_example(labels: list) -> str:
    """
    Mapea múltiples emociones de GoEmotions a una emoción principal de Synapse.
    
    Args:
        labels: Lista de emociones de GoEmotions
    
    Returns:
        Emoción principal de Synapse
    """
    if not labels:
        return "neutral"
    
    # Mapear todas las emociones
    mapped = [map_emotion(label) for label in labels]
    
    # Contar frecuencias
    from collections import Counter
    counts = Counter(mapped)
    
    # Prioridad de emociones (si hay empate)
    priority = [
        "desesperado",  # Emociones negativas fuertes primero
        "frustracion",
        "ansiedad",
        "abrumado",
        "confusion",
        "neutral",
        "curiosidad",
        "motivacion",
    ]
    
    # Devolver la emoción más frecuente, con prioridad
    for emotion in priority:
        if emotion in counts:
            return emotion
    
    return "neutral"


def process_goemotions_dataset():
    """Procesa el dataset GoEmotions ES y aplica el mapeo de emociones."""
    
    print("=" * 60)
    print("MAPEO DE EMOCIONES: GOEMOTIONS → SYNAPSE")
    print("=" * 60)
    
    # Cargar dataset
    json_path = RAW_DIR / "goemotions_es.json"
    
    if not json_path.exists():
        print("✗ Error: No se encontró el dataset GoEmotions ES")
        print("  Ejecuta primero: python download_goemotions.py")
        return False
    
    print(f"\nCargando dataset desde: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"  - Ejemplos: {len(data)}")
    
    # Contar emociones originales
    print("\nDistribución de emociones originales (top 10):")
    all_original = []
    for example in data:
        all_original.extend(example["labels"])
    
    original_counts = Counter(all_original)
    for emotion, count in original_counts.most_common(10):
        print(f"  {emotion}: {count}")
    
    # Aplicar mapeo
    print("\nAplicando mapeo de emociones...")
    mapped_data = []
    
    for example in data:
        # Mapear emociones
        synapse_emotion = map_emotions_for_example(example["labels"])
        
        mapped_data.append({
            "text": example["text"],
            "emocion_goemotions": example["labels"],
            "emocion_synapse": synapse_emotion,
            "id": example["id"],
            "split": example["split"]
        })
    
    # Contar emociones mapeadas
    print("\nDistribución de emociones Synapse:")
    synapse_counts = Counter([d["emocion_synapse"] for d in mapped_data])
    for emotion, count in synapse_counts.most_common():
        print(f"  {emotion}: {count}")
    
    # Guardar resultado
    output_path = PROCESSED_DIR / "goemotions_mapped.json"
    print(f"\nGuardando dataset mapeado: {output_path}")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(mapped_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Guardado: {output_path}")
    print(f"  - Tamaño: {output_path.stat().st_size / 1024:.1f} KB")
    print(f"  - Ejemplos: {len(mapped_data)}")
    
    # Mostrar muestra
    print("\n" + "=" * 60)
    print("MUESTRA DE DATOS MAPEADOS")
    print("=" * 60)
    for i, example in enumerate(mapped_data[:5]):
        print(f"\n--- Ejemplo {i+1} ---")
        print(f"  Texto: {example['text'][:80]}...")
        print(f"  GoEmotions: {example['emocion_goemotions']}")
        print(f"  Synapse: {example['emocion_synapse']}")
    
    print("\n" + "=" * 60)
    print("MAPEO COMPLETADO")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success = process_goemotions_dataset()
    sys.exit(0 if success else 1)
