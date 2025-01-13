# Data Deduplication

This repository contains a set of scripts and tools for performing data deduplication on large datasets. It includes the following components:

- **Scripts**: For calculating hashes of text data and removing duplicates.
- **Docker Compose**: For running Elasticsearch as a service.
- **Requirements**: The necessary dependencies for running the scripts.
- **.env**: Configuration for environment variables.

## Overview

The main goal of this project is to help eliminate duplicate data in a dataset based on text hashes. It uses Elasticsearch to track duplicate hashes and perform efficient lookup operations.

### Scripts

- `get_repeated_hashes.py`: This script calculates SHA-256 hashes for each text in a dataset and checks them against Elasticsearch to find duplicates.
- `remove_duplicates.py`: This script removes the duplicate entries from the dataset using the hashes found by `get_repeated_hashes.py`.
- `index_documents.py`: This script indexes the documents in Elasticsearch. It is used to populate the Elasticsearch index with the documents from the dataset.
- `requirements.txt`: Lists the required Python packages for running the scripts.
- `.env.example`: An example environment file for configuring Elasticsearch connection settings.

## Requirements

- Docker and Docker Compose
- Python 3.7+
- Elasticsearch (configured via Docker Compose)

## Setup

### 1. Clone the repository

Clone the repository to your local machine:

```bash
git clone https://github.com/yourusername/data-deduplication.git
cd data-deduplication
```

### 2. Install dependencies
```bash
pip install -r requirements/base.txt
```

### 3. Configure Elasticsearch
The project includes a docker-compose.yml file to easily spin up an Elasticsearch container. To set up Elasticsearch:

#### 1. Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```

#### 2. Modify the `.env` file to configure your Elasticsearch credentials and other environment variables as needed.

### 4. Start Elasticsearch with Docker Compose
Use the following command to start Elasticsearch:
```bash
docker-compose up -d
```
This will pull the necessary Docker image and start an Elasticsearch container running on localhost:9200.

### 5. Run the scripts
To index the documents from your dataset in Elasticsearch, run:
```bash
python index_documents.py --dataset_path "/path/to/dataset" --index_name "your_index_name" --column_to_index "your_column_name"
```
To find repeated hashes in your dataset, run:
```bash
python get_repeated_hashes.py --dataset_path "/path/to/dataset" --num_processes num_processes --output_path "/path/to/output" --index "index_name"
```

To remove duplicates from the dataset based on the repeated hashes, run:
```bash
python remove_duplicates.py --dataset_path "/path/to/dataset" --duplicated_hashes_path "/path/to/hashes_repetidos" --output_dir "/path/to/output" --chunk_size chunk_size
```

### 6. Stop Elasticsearch
When you’re done, stop the Elasticsearch container with:
```bash
docker-compose down
```
