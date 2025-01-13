import argparse
import hashlib
import os
from multiprocessing import Manager, Process

from datasets import Dataset, load_from_disk
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from tqdm import tqdm

from index_documents import dividir_dataset


def buscar_documento_por_texto(
    es: Elasticsearch, indice: str, texto_query: str
) -> list:
    """
    Busca documentos en un índice de Elasticsearch donde el campo 'texto'
    coincida exactamente con el texto proporcionado.

    Args:
        es (Elasticsearch): Instancia de Elasticsearch.
        indice (str): Nombre del índice donde buscar.
        texto_query (str): Texto exacto a buscar en el campo 'texto'.

    Returns:
        list: Lista de documentos que coinciden con la consulta exacta.
    """
    query = {"query": {"term": {"texto": texto_query}}}

    try:
        respuesta = es.search(index=indice, body=query)
        documentos = [hit["_source"] for hit in respuesta["hits"]["hits"]]
        return documentos
    except Exception as e:
        print(f"Error al realizar la búsqueda: {e}")
        return []


def calcular_hash(texto: str) -> str:
    """
    Calcula el hash SHA-256 de un texto.

    Args:
        texto (str): Texto a ser procesado.

    Returns:
        str: Hash SHA-256 del texto.
    """
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def procesar_chunk(
    chunk: Dataset, lock, hashes_repetidos: list, index: str, es: Elasticsearch
) -> None:
    """
    Procesa un chunk de documentos del dataset, buscando su hash en
    Elasticsearch y actualizando los contadores globales.

    Args:
        chunk (Dataset): Chunk del dataset a procesar.
        lock (Lock): Bloqueo para sincronizar actualizaciones de contadores.
        hashes_repetidos (list): Lista global de hashes repetidos.
        index (str): Nombre del índice de Elasticsearch.
        es (Elasticsearch): Instancia de Elasticsearch.
    """
    hashes = []
    for example in tqdm(chunk):
        try:
            texto = example["texto"]
            _hash = calcular_hash(texto)
            meta_list = buscar_documento_por_texto(es, index, _hash)

            hashes.append(_hash)

            with lock:
                if len(meta_list) > 1:
                    hashes_repetidos.append(_hash)

        except Exception as e:
            print(f"Error al procesar el documento: {e}")
            pass


def main(args):
    load_dotenv()
    es = Elasticsearch(
        hosts=["http://localhost:9200"],
        basic_auth=("elastic", os.getenv("ELASTIC_PASSWORD")),
    )

    dataset = load_from_disk(args.dataset_path)
    manager = Manager()
    lock = manager.Lock()

    hashes_repetidos = manager.list()

    num_processes = args.num_processes
    chunks = dividir_dataset(dataset, num_processes)
    procesos = []

    for i, chunk in enumerate(chunks):
        proceso = Process(
            target=procesar_chunk, args=(chunk, lock, hashes_repetidos, args.index, es)
        )
        procesos.append(proceso)

    for proceso in procesos:
        proceso.start()

    for proceso in procesos:
        proceso.join()

    dataset_hashes = Dataset.from_dict({"hash": list(hashes_repetidos)})
    dataset_hashes.save_to_disk(args.output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Procesamiento de hashes repetidos en un dataset "
            "y almacenamiento en Elasticsearch."
        )
    )
    parser.add_argument(
        "--dataset_path",
        type=str,
        required=True,
        help="Ruta del dataset de Hugging Face.",
    )
    parser.add_argument(
        "--num_processes",
        type=int,
        default=50,
        help="Número de procesos para paralelizar el procesamiento del dataset.",
    )
    parser.add_argument(
        "--output_path",
        type=str,
        required=True,
        help="Ruta donde guardar el dataset con los hashes repetidos.",
    )
    parser.add_argument(
        "--index",
        type=str,
        required=True,
        help="Nombre del índice de Elasticsearch a utilizar.",
    )

    args = parser.parse_args()
    main(args)
