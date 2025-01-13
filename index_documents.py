import argparse
import multiprocessing
import os

from datasets import Dataset, load_from_disk
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from tqdm import tqdm


def dividir_dataset(dataset: Dataset, n_chunks: int) -> list:
    """
    Divide un dataset de Hugging Face en n chunks, manteniendo
    cada chunk como un objeto Dataset.

    Args:
        dataset (Dataset): El dataset de Hugging Face que se desea dividir.
        n_chunks (int): El número de chunks en los que dividir el dataset.

    Returns:
        list: Lista de objetos Dataset, cada uno correspondiente a un
        chunk del dataset original.
    """
    chunk_size = len(dataset) // n_chunks
    chunks = []

    for i in range(n_chunks):
        start_idx = i * chunk_size
        end_idx = (i + 1) * chunk_size if i < n_chunks - 1 else len(dataset)
        chunk = dataset.select(range(start_idx, end_idx))
        chunks.append(chunk)

    return chunks


def create_index(es_client: Elasticsearch, index_name: str) -> dict:
    """
    Crea un índice en Elasticsearch con un campo 'texto' de tipo 'keyword'.

    Args:
        es_client (Elasticsearch): Cliente de Elasticsearch.
        index_name (str): Nombre del índice a crear.

    Returns:
        dict: Respuesta de Elasticsearch sobre la creación del índice.
    """
    mapping = {"mappings": {"properties": {"texto": {"type": "keyword"}}}}

    response = es_client.indices.create(index=index_name, body=mapping, ignore=400)
    return response


def index_chunk(
    chunk, index_name: str, es_host: str, auth: tuple, column_name: str, offset: int
) -> None:
    """
    Indexa un chunk de datos en Elasticsearch.

    Args:
        chunk (Dataset): Chunk del dataset.
        index_name (str): Nombre del índice donde se almacenarán los datos.
        es_host (str): Dirección del host de Elasticsearch.
        auth (tuple): Credenciales para Elasticsearch.
        column_name (str): Nombre de la columna a indexar.
        offset (int): Desplazamiento inicial para los IDs de los documentos.

    Returns:
        None
    """
    es_client = Elasticsearch(hosts=[es_host], basic_auth=auth)

    for i, record in enumerate(
        tqdm(chunk, desc=f"Indexando chunk con offset {offset}")
    ):
        text = record.get(column_name)
        if text:
            doc_id = offset + i
            doc = {"texto": text}
            es_client.index(index=index_name, id=doc_id, body=doc)


def process_chunk(
    chunk, index_name: str, es_host: str, auth: tuple, column_name: str, offset: int
):
    """
    Función envolvente para ejecutar index_chunk como un proceso independiente.

    Args:
        chunk (Dataset): Chunk del dataset.
        index_name (str): Nombre del índice donde se almacenarán los datos.
        es_host (str): Dirección del host de Elasticsearch.
        auth (tuple): Credenciales para Elasticsearch.
        column_name (str): Nombre de la columna a indexar.
        offset (int): Desplazamiento inicial para los IDs de los documentos.

    Returns:
        None
    """
    index_chunk(chunk, index_name, es_host, auth, column_name, offset)


if __name__ == "__main__":
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Indexación de datos en Elasticsearch."
    )
    parser.add_argument(
        "index_name", type=str, help="Nombre del índice en Elasticsearch"
    )
    parser.add_argument("dataset_path", type=str, help="Ruta al dataset en disco")
    parser.add_argument(
        "column_to_index", type=str, help="Nombre de la columna a indexar"
    )
    args = parser.parse_args()

    es_host = "http://localhost:9200"
    es_auth = ("elastic", os.getenv("ELASTIC_PASSWORD"))

    es = Elasticsearch(hosts=[es_host], basic_auth=es_auth)

    print(f"Creando índice '{args.index_name}' en Elasticsearch...")
    response = create_index(es, args.index_name)

    dataset = load_from_disk(args.dataset_path)

    num_processes = os.cpu_count()
    print(f"Dividiendo el dataset en {num_processes} chunks...")
    chunks = dividir_dataset(dataset, num_processes)

    processes = []
    for i, chunk in enumerate(chunks):
        offset = i * len(chunks[0])
        process = multiprocessing.Process(
            target=process_chunk,
            args=(
                chunk,
                args.index_name,
                es_host,
                es_auth,
                args.column_to_index,
                offset,
            ),
        )
        processes.append(process)
        process.start()

    for process in processes:
        process.join()

    print("Indexación completada.")
