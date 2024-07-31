import pytest
from algokit_utils import (
    get_algod_client,
    get_default_localnet_config,
    get_indexer_client,
)
from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient

# Uncomment if you want to load network specific or generic .env file
# @pytest.fixture(autouse=True, scope="session")
# def environment_fixture() -> None:
#     env_path = Path(__file__).parent.parent / ".env"
#     load_dotenv(env_path)


@pytest.fixture(scope="session")
def algod_client() -> AlgodClient:
    # by default we are using localnet algod
    client = get_algod_client(get_default_localnet_config("algod"))
    return client


@pytest.fixture(scope="session")
def indexer_client() -> IndexerClient:
    return get_indexer_client(get_default_localnet_config("indexer"))
