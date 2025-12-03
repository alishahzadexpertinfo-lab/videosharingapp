import os
from azure.cosmos import CosmosClient, PartitionKey

COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")

if not COSMOS_ENDPOINT or not COSMOS_KEY:
    # It is fine to import the module without these, but runtime operations will fail.
    # Make it explicit in logs when client is first created.
    print("Warning: COSMOS_ENDPOINT or COSMOS_KEY not set. Set them as environment variables.")

def get_cosmos_client() -> CosmosClient:
    return CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY)


def _get_or_create_database(client: CosmosClient, db_name: str):
    try:
        database = client.create_database_if_not_exists(id=db_name)
    except Exception:
        database = client.get_database_client(db_name)
    return database


def _get_or_create_container(database, container_name: str, partition_key_path: str):
    try:
        container = database.create_container_if_not_exists(
            id=container_name,
            partition_key=PartitionKey(path=partition_key_path),
            offer_throughput=400,
        )
    except Exception:
        container = database.get_container_client(container_name)
    return container


def get_container_videos(client: CosmosClient, db_name: str, container_name: str):
    db = _get_or_create_database(client, db_name)
    # Partition key on id keeps it simple here; for very large scale you might choose user_id.
    return _get_or_create_container(db, container_name, partition_key_path="/id")


def get_container_users(client: CosmosClient, db_name: str, container_name: str):
    db = _get_or_create_database(client, db_name)
    return _get_or_create_container(db, container_name, partition_key_path="/id")


def get_container_comments(client: CosmosClient, db_name: str, container_name: str):
    db = _get_or_create_database(client, db_name)
    return _get_or_create_container(db, container_name, partition_key_path="/id")
