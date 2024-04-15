import algokit_utils
import algosdk.error
import pytest
from algokit_utils import Account
from algokit_utils.beta.account_manager import AddressAndSigner
from algokit_utils.beta.algorand_client import (
    AlgorandClient,
    AssetCreateParams,
    AssetOptInParams,
    AssetTransferParams,
    PayParams,
)
from algokit_utils.config import config
from algosdk.atomic_transaction_composer import TransactionWithSigner

from smart_contracts.artifacts.digital_marketplace.client import (
    DigitalMarketplaceClient,
)


@pytest.fixture(scope="session")
def algorand() -> AlgorandClient:
    client: AlgorandClient = AlgorandClient.default_local_net()
    return client

@pytest.fixture(scope="session")
def dispenser(algorand: AlgorandClient) -> AddressAndSigner:
    return algorand.account.dispenser()

@pytest.fixture(scope="session")
def creator(algorand: AlgorandClient, dispenser: AddressAndSigner) -> AddressAndSigner:
    acct = algorand.account.random()
    algorand.send.payment(PayParams(
        sender=dispenser.address,
        receiver=acct.address,
        amount=10_000_000
    ))
    return acct

@pytest.fixture(scope="session")
def test_asset_id(creator: Account, algorand: AlgorandClient) -> int:
    sent_txn = algorand.send.asset_create(
        AssetCreateParams(
            sender=creator.address,
            total=10
        )
    )

    return sent_txn["confirmation"]["asset-index"]


@pytest.fixture(scope="session")
def digital_marketplace_client(
    test_asset_id: int,
    creator: Account,
    algorand: AlgorandClient,
) -> DigitalMarketplaceClient:
    config.configure(
        debug=True,
        # trace_all=True,
    )

    client = DigitalMarketplaceClient(
        algod_client=algorand.client.algod,
        sender=creator.address,
        signer=creator.signer
    )

    client.create_create_application(unitary_price=0, asset_id=test_asset_id)
    return client


def test_opt_in_to_asset(
    digital_marketplace_client: DigitalMarketplaceClient,
    creator: Account,
    test_asset_id: int,
    algorand: AlgorandClient
) -> None:
    pytest.raises(
        algosdk.error.AlgodHTTPError,
        lambda: algorand.account.get_asset_information(
            digital_marketplace_client.app_address, test_asset_id
        ),
    )


    mbr_pay_txn =  algorand.transactions.payment(PayParams(
        sender=creator.address,
        receiver=digital_marketplace_client.app_address,
        amount=200_000,
        extra_fee=1_000
    ))

    result = digital_marketplace_client.opt_in_to_asset(
        mbr_pay=TransactionWithSigner(
            txn=mbr_pay_txn,
            signer=creator.signer
        ),
        transaction_parameters=algokit_utils.TransactionParameters(
            foreign_assets=[test_asset_id]
        ),
    )

    assert result.confirmed_round

    assert (
        algorand.account.get_asset_information(
            digital_marketplace_client.app_address, test_asset_id
        )["asset-holding"]["amount"]
        == 0
    )


def test_deposit(
    digital_marketplace_client: DigitalMarketplaceClient,
    creator: Account,
    test_asset_id: int,
    algorand: AlgorandClient
):
    result = algorand.send.asset_transfer(AssetTransferParams(
        sender=creator.address,
        asset_id=test_asset_id,
        receiver=digital_marketplace_client.app_address,
        amount=3
    ))

    assert result

    assert (
        algorand.account.get_asset_information(
            digital_marketplace_client.app_address, test_asset_id
        )["asset-holding"]["amount"]
        == 3
    )


def test_set_price(digital_marketplace_client: DigitalMarketplaceClient):
    result = digital_marketplace_client.set_price(unitary_price=3_300_000)

    assert result.confirmed_round


def test_buy(digital_marketplace_client: DigitalMarketplaceClient, test_asset_id: int, algorand: AlgorandClient, dispenser: AddressAndSigner):
    buyer = algorand.account.random()

    algorand.send.payment(PayParams(
        sender=dispenser.address,
        receiver=buyer.address,
        amount=10_000_000
    ))

    algorand.send.asset_opt_in(AssetOptInParams(
        asset_id=test_asset_id,
        sender=buyer.address,
    ))

    buyer_payment_txn = algorand.transactions.payment(PayParams(
        sender=buyer.address,
        receiver=digital_marketplace_client.app_address,
        amount=6_600_000,
        extra_fee=1_000
    ))

    result = digital_marketplace_client.buy(
        buyer_txn=TransactionWithSigner(
            txn=buyer_payment_txn,
            signer=buyer.signer,
        ),
        quantity=2,
        transaction_parameters=algokit_utils.TransactionParameters(
            sender=buyer.address,
            signer=buyer.signer,
            foreign_assets=[test_asset_id]
        ),
    )

    assert result.confirmed_round

    assert (
        algorand.account.get_asset_information(
            buyer.address, test_asset_id
        )["asset-holding"]["amount"]
        == 2
    )


def test_delete_application(
    digital_marketplace_client: DigitalMarketplaceClient,
    creator: Account,
    test_asset_id: int,
    algorand: AlgorandClient
):
    before_call_amount = algorand.account.get_information(
        creator.address
    )["amount"]

    sp_call = digital_marketplace_client.algod_client.suggested_params()
    sp_call.flat_fee = True
    sp_call.fee = 3_000
    result = digital_marketplace_client.delete_delete_application(
        transaction_parameters=algokit_utils.TransactionParameters(
            suggested_params=sp_call,
            foreign_assets=[test_asset_id]
        ),
    )

    assert result.confirmed_round

    after_call_amount = algorand.account.get_information(
        creator.address
    )["amount"]

    assert after_call_amount - before_call_amount == 6_600_000 + 200_000 - 3_000
    assert (
        algorand.account.get_asset_information(
            creator.address, test_asset_id
        )["asset-holding"]["amount"]
        == 8
    )
