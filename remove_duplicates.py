import argparse
import gc
import hashlib
from collections import Counter

from datasets import Dataset, load_from_disk
from tqdm import tqdm


def calcular_hash(texto: str) -> str:
    """
    Calcula el hash SHA-256 de un texto.

    Args:
        texto (str): El texto a procesar.

    Returns:
        str: El hash SHA-256 del texto.
    """
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def procesar_dataset(
    dataset_path: str,
    duplicated_hashes_path: str,
    output_dir: str,
    chunk_size: int = 500000,
) -> None:
    """
    Elimina los duplicados del dataset basándose en los hashes y
    guarda los resultados en chunks.

    Args:
        dataset_path (str): Ruta del dataset de entrada.
        duplicated_hashes_path (str): Ruta del archivo que contiene los
        hashes repetidos.
        output_dir (str): Directorio donde guardar los datasets procesados.
        chunk_size (int): Tamaño de cada chunk de datos guardados (por defecto 500000).
    """
    dataset = load_from_disk(dataset_path)
    duplicated_hashes = load_from_disk(duplicated_hashes_path)["hash"]
    hash_count = dict(Counter(duplicated_hashes))

    textos = []
    metas = []
    chunk = 0

    for example in tqdm(dataset, desc="Procesando dataset"):
        example_hash = calcular_hash(example["texto"])

        repeat_number = hash_count.get(example_hash, 0)

        if repeat_number > 1:
            hash_count[example_hash] -= 1
            continue
        elif repeat_number == 1:
            textos.append(example["texto"])
            metas.append(example["meta"])
            del hash_count[example_hash]

        if len(metas) >= chunk_size:
            guardar_chunk(textos, metas, output_dir, chunk)
            chunk += 1
            textos, metas = [], []
            gc.collect()

    if textos and metas:
        guardar_chunk(textos, metas, output_dir, chunk)


def guardar_chunk(textos: list, metas: list, output_dir: str, chunk: int) -> None:
    """
    Guarda un chunk del dataset procesado en el directorio especificado.

    Args:
        textos (list): Lista de textos procesados.
        metas (list): Lista de metadatos procesados.
        output_dir (str): Directorio donde guardar el chunk.
        chunk (int): Número del chunk actual.
    """
    dataset_chunk = Dataset.from_dict(
        {
            "texto": textos,
            "meta": metas,
        }
    )
    output_path = f"{output_dir}/rp_deduped_chunk_{chunk}"
    dataset_chunk.save_to_disk(output_path)


def main(args):
    procesar_dataset(
        args.dataset_path, args.duplicated_hashes_path, args.output_dir, args.chunk_size
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Elimina los duplicados de un dataset basándose en los hashes "
            "y guarda los resultados en chunks."
        )
    )
    parser.add_argument(
        "--dataset_path",
        type=str,
        required=True,
        help="Ruta del dataset de Hugging Face.",
    )
    parser.add_argument(
        "--duplicated_hashes_path",
        type=str,
        required=True,
        help="Ruta del archivo que contiene los hashes duplicados.",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
        help="Directorio donde guardar los datasets procesados.",
    )
    parser.add_argument(
        "--chunk_size",
        type=int,
        default=500000,
        help="Tamaño de cada chunk de datos guardados (por defecto 500000).",
    )

    args = parser.parse_args()
    main(args)
