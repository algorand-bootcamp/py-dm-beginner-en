import algokit_utils
import algosdk
import pytest
from algokit_utils.beta.account_manager import AddressAndSigner
from algokit_utils.beta.algorand_client import (
    AlgorandClient,
    AssetCreateParams,
    AssetOptInParams,
    AssetTransferParams,
    PayParams,
)
from algosdk.atomic_transaction_composer import TransactionWithSigner

from smart_contracts.artifacts.digital_marketplace.client import (
    DigitalMarketplaceClient,
)


@pytest.fixture(scope="session")
def algorand() -> AlgorandClient:
    """Get an AlgorandClient to use throughout the tests"""
    return AlgorandClient.default_local_net()


@pytest.fixture(scope="session")
def dispenser(algorand: AlgorandClient) -> AddressAndSigner:
    """Get the dispenser to fund test addresses"""
    return algorand.account.dispenser()


@pytest.fixture(scope="session")
def creator(algorand: AlgorandClient, dispenser: AddressAndSigner) -> AddressAndSigner:
    acct = algorand.account.random()

    algorand.send.payment(
        PayParams(sender=dispenser.address, receiver=acct.address, amount=10_000_000)
    )

    return acct


@pytest.fixture(scope="session")
def test_asset_id(creator: AddressAndSigner, algorand: AlgorandClient) -> int:
    sent_txn = algorand.send.asset_create(
        AssetCreateParams(sender=creator.address, total=10)
    )

    return sent_txn["confirmation"]["asset-index"]


@pytest.fixture(scope="session")
def digital_marketplace_client(
    algorand: AlgorandClient, creator: AddressAndSigner, test_asset_id: int
) -> DigitalMarketplaceClient:
    """Instantiate an aplpication client we can use for our tests"""
    client = DigitalMarketplaceClient(
        algod_client=algorand.client.algod,
        sender=creator.address,
        signer=creator.signer,
    )

    client.create_create_application(unitary_price=0, asset_id=test_asset_id)

    return client


def test_opt_in_to_asset(
    digital_marketplace_client: DigitalMarketplaceClient,
    creator: AddressAndSigner,
    test_asset_id: int,
    algorand: AlgorandClient,
):
    # ensure get_asset_information throws an error because the app is not yet opted in
    pytest.raises(
        algosdk.error.AlgodHTTPError,
        lambda: algorand.account.get_asset_information(
            digital_marketplace_client.app_address, test_asset_id
        ),
    )

    # We need to send 100_000 uALGO for account MBR and 100_000 uALGO for ASA MBR
    mbr_pay_txn = algorand.transactions.payment(
        PayParams(
            sender=creator.address,
            receiver=digital_marketplace_client.app_address,
            amount=200_000,
            extra_fee=1_000,
        )
    )

    result = digital_marketplace_client.opt_in_to_asset(
        mbr_pay=TransactionWithSigner(txn=mbr_pay_txn, signer=creator.signer),
        transaction_parameters=algokit_utils.TransactionParameters(
            # We are using this asset in the contract, thus we need to tell the AVM its asset ID
            # In the near future, this will be done automatically
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
    creator: AddressAndSigner,
    test_asset_id: int,
    algorand: AlgorandClient,
):
    result = algorand.send.asset_transfer(
        AssetTransferParams(
            sender=creator.address,
            receiver=digital_marketplace_client.app_address,
            asset_id=test_asset_id,
            amount=3,
        )
    )

    assert result["confirmation"]

    assert (
        algorand.account.get_asset_information(
            digital_marketplace_client.app_address, test_asset_id
        )["asset-holding"]["amount"]
        == 3
    )


def test_set_price(digital_marketplace_client: DigitalMarketplaceClient):
    result = digital_marketplace_client.set_price(unitary_price=3_300_000)

    assert result.confirmed_round


def test_buy(
    digital_marketplace_client: DigitalMarketplaceClient,
    creator: AddressAndSigner,
    test_asset_id: int,
    algorand: AlgorandClient,
    dispenser: AddressAndSigner,
):
    # create new account to be the buyer
    buyer = algorand.account.random()

    # use the dispenser to fund buyer
    algorand.send.payment(
        PayParams(sender=dispenser.address, receiver=buyer.address, amount=10_000_000)
    )

    # opt the buyer into the asset
    algorand.send.asset_opt_in(
        AssetOptInParams(sender=buyer.address, asset_id=test_asset_id)
    )

    # form a transaction to buy two assets (2 * 3_300_000)
    buyer_payment_txn = algorand.transactions.payment(
        PayParams(
            sender=buyer.address,
            receiver=digital_marketplace_client.app_address,
            amount=2 * 3_300_000,
            extra_fee=1_000,
        )
    )

    result = digital_marketplace_client.buy(
        buyer_txn=TransactionWithSigner(txn=buyer_payment_txn, signer=buyer.signer),
        quantity=2,
        transaction_parameters=algokit_utils.TransactionParameters(
            sender=buyer.address,
            signer=buyer.signer,
            # we need to tell the AVM about the asset the call will use
            foreign_assets=[test_asset_id],
        ),
    )

    assert result.confirmed_round

    assert (
        algorand.account.get_asset_information(buyer.address, test_asset_id)[
            "asset-holding"
        ]["amount"]
        == 2
    )


def test_delete_application(
    digital_marketplace_client: DigitalMarketplaceClient,
    creator: AddressAndSigner,
    test_asset_id: int,
    algorand: AlgorandClient,
    dispenser: AddressAndSigner,
):
    before_call_amount = algorand.account.get_information(creator.address)["amount"]

    result = digital_marketplace_client.delete_delete_application(
        transaction_parameters=algokit_utils.TransactionParameters(
            # we are sending the asset in the call, so we need to tell the AVM
            foreign_assets=[test_asset_id],
        )
    )

    assert result.confirmed_round

    after_call_amount = algorand.account.get_information(creator.address)["amount"]

    assert after_call_amount - before_call_amount == (2 * 3_300_000) + 200_000 - 3_000
    assert (
        algorand.account.get_asset_information(creator.address, test_asset_id)[
            "asset-holding"
        ]["amount"]
        == 8
    )
