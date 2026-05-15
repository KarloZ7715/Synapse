#!/usr/bin/env python3
"""
Script para descargar el dataset GoEmotions Multilingüe desde HuggingFace.

Fuente: AnasAlokla/multilingual_go_emotions
- 325K+ filas totales
- Español incluido (language: "sp")
- 28 emociones multi-label (IDs)
- Licencia: Apache 2.0

Uso:
    python download_goemotions.py
"""

import os
import sys
import json
from pathlib import Path

# Configurar paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
RAW_DIR = PROJECT_ROOT / "dataset" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Mapeo de IDs a nombres de emociones GoEmotions
GOEMOTIONS_LABELS = {
    0: "admiration",
    1: "amusement",
    2: "anger",
    3: "annoyance",
    4: "approval",
    5: "caring",
    6: "confusion",
    7: "curiosity",
    8: "desire",
    9: "disappointment",
    10: "disapproval",
    11: "disgust",
    12: "embarrassment",
    13: "excitement",
    14: "fear",
    15: "gratitude",
    16: "grief",
    17: "joy",
    18: "love",
    19: "nervousness",
    20: "optimism",
    21: "pride",
    22: "realization",
    23: "relief",
    24: "remorse",
    25: "sadness",
    26: "surprise",
    27: "neutral",
}


def download_goemotions():
    """Descarga el dataset GoEmotions Multilingüe y filtra español."""
    
    try:
        from datasets import load_dataset
    except ImportError:
        print("Error: La librería 'datasets' no está instalada.")
        print("Instala con: pip install datasets")
        sys.exit(1)
    
    print("=" * 60)
    print("DESCARGA DE GOEMOTIONS MULTILINGÜE")
    print("=" * 60)
    print(f"\nDataset: AnasAlokla/multilingual_go_emotions")
    print(f"Destino: {RAW_DIR}")
    print()
    
    try:
        # Descargar dataset
        print("Descargando dataset desde HuggingFace...")
        dataset = load_dataset("AnasAlokla/multilingual_go_emotions")
        
        # Mostrar información del dataset
        print(f"\n✓ Dataset descargado exitosamente")
        print(f"  - Splits: {list(dataset.keys())}")
        print(f"  - Columnas: {list(dataset['train'].features.keys())}")
        
        # Filtrar solo español
        print("\nFiltrando ejemplos en español...")
        spanish_examples = []
        
        for split_name in dataset.keys():
            for example in dataset[split_name]:
                if example.get("language") == "sp":
                    # Parsear etiquetas (vienen como string "[15, 17]")
                    labels_str = example["labels"]
                    if isinstance(labels_str, str):
                        # Limpiar string y convertir a lista de ints
                        labels_str = labels_str.strip("[]")
                        if labels_str:
                            emotion_ids = [int(x.strip()) for x in labels_str.split(",")]
                        else:
                            emotion_ids = []
                    else:
                        emotion_ids = labels_str
                    
                    # Convertir IDs a nombres de emociones
                    emotion_names = [GOEMOTIONS_LABELS.get(int(id_), "unknown") for id_ in emotion_ids]
                    
                    spanish_examples.append({
                        "text": example["text"],
                        "labels": emotion_names,
                        "label_ids": emotion_ids,
                        "id": example["id"],
                        "split": split_name
                    })
        
        print(f"  - Ejemplos en español encontrados: {len(spanish_examples)}")
        
        if len(spanish_examples) == 0:
            print("✗ Error: No se encontraron ejemplos en español")
            return False
        
        # Guardar como JSON
        json_path = RAW_DIR / "goemotions_es.json"
        print(f"\nGuardando dataset: {json_path}")
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(spanish_examples, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Guardado: {json_path}")
        print(f"  - Tamaño: {json_path.stat().st_size / 1024:.1f} KB")
        print(f"  - Ejemplos: {len(spanish_examples)}")
        
        # Guardar como CSV
        csv_path = RAW_DIR / "goemotions_es.csv"
        print(f"\nGuardando como CSV: {csv_path}")
        
        import pandas as pd
        df = pd.DataFrame(spanish_examples)
        df.to_csv(csv_path, index=False, encoding='utf-8')
        
        print(f"✓ Guardado: {csv_path}")
        print(f"  - Tamaño: {csv_path.stat().st_size / 1024:.1f} KB")
        
        # Mostrar muestra de datos
        print("\n" + "=" * 60)
        print("MUESTRA DE DATOS")
        print("=" * 60)
        for i, example in enumerate(spanish_examples[:5]):
            print(f"\n--- Ejemplo {i+1} ---")
            print(f"  Texto: {example['text'][:100]}...")
            print(f"  Emociones: {example['labels']}")
        
        # Estadísticas de emociones
        print("\n" + "=" * 60)
        print("ESTADÍSTICAS DE EMOCIONES")
        print("=" * 60)
        from collections import Counter
        
        all_emotions = []
        for example in spanish_examples:
            all_emotions.extend(example["labels"])
        
        emotion_counts = Counter(all_emotions)
        print("\nTop 10 emociones más frecuentes:")
        for emotion, count in emotion_counts.most_common(10):
            print(f"  {emotion}: {count}")
        
        print("\n" + "=" * 60)
        print("DESCARGA COMPLETADA")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error durante la descarga: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = download_goemotions()
    sys.exit(0 if success else 1)
