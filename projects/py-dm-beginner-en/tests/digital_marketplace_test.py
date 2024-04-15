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
    """Get an AlgorandClient to use throughout the tests"""
    client: AlgorandClient = AlgorandClient.default_local_net()
    return client

@pytest.fixture(scope="session")
def dispenser(algorand: AlgorandClient) -> AddressAndSigner:
    """Get the dispenser address to fund test address"""
    return algorand.account.dispenser()

@pytest.fixture(scope="session")
def creator(algorand: AlgorandClient, dispenser: AddressAndSigner) -> AddressAndSigner:
    """Get an account that will be used to create the contract"""
    acct = algorand.account.random()
    algorand.send.payment(PayParams(
        sender=dispenser.address,
        receiver=acct.address,
        amount=10_000_000
    ))
    return acct

@pytest.fixture(scope="session")
def test_asset_id(creator: Account, algorand: AlgorandClient) -> int:
    """Create an asset to use throughout the tests"""
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
    """Instantiate an application client that we can use throughout the rest of the tests and deploy it to localnet"""
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
    # get_asset_information throws an error when an account is not opted in
    pytest.raises(
        algosdk.error.AlgodHTTPError,
        lambda: algorand.account.get_asset_information(
            digital_marketplace_client.app_address, test_asset_id
        ),
    )


    # We need to send 200_000 uALGO to the contract to cover the account + asset MBR
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
            # Since we are using an asset in the contract call, we need to predefine the asset in the foreign_assets array
            # In the near future, this will be done automatically
            foreign_assets=[test_asset_id]
        ),
    )

    # make sure the txn was confirmed
    assert result.confirmed_round

    # get_asset_information will no longer throw an error and show the amount is 0 now that the app is opted in
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
    # transfer 3 of the ASA to the app
    result = algorand.send.asset_transfer(AssetTransferParams(
        sender=creator.address,
        asset_id=test_asset_id,
        receiver=digital_marketplace_client.app_address,
        amount=3
    ))

    # ensure the transfer was confirmed
    assert result["confirmation"]

    # The app should now hold 3 of the given asset
    assert (
        algorand.account.get_asset_information(
            digital_marketplace_client.app_address, test_asset_id
        )["asset-holding"]["amount"]
        == 3
    )


def test_set_price(digital_marketplace_client: DigitalMarketplaceClient):
    """Set price"""
    result = digital_marketplace_client.set_price(unitary_price=3_300_000)

    assert result.confirmed_round


def test_buy(digital_marketplace_client: DigitalMarketplaceClient, test_asset_id: int, algorand: AlgorandClient, dispenser: AddressAndSigner):
    # get a new account to be the buyer
    buyer = algorand.account.random()

    # user the dispenser to fund the buyer
    algorand.send.payment(PayParams(
        sender=dispenser.address,
        receiver=buyer.address,
        amount=10_000_000
    ))

    # opt the buyer into the asset
    algorand.send.asset_opt_in(AssetOptInParams(
        asset_id=test_asset_id,
        sender=buyer.address,
    ))

    # form a transaction to buy two (2 * 3_300_000) of the asset
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
            # send this method call from the buyer
            sender=buyer.address,
            signer=buyer.signer,
            # the contract uses the asset, so we must put it in foreign_assets
            foreign_assets=[test_asset_id]
        ),
    )

    # ensure the app call was confirmed
    assert result.confirmed_round

    # the buyer should now have two of the asset
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
    # record the amount the creator has before deleting the app
    before_call_amount = algorand.account.get_information(
        creator.address
    )["amount"]

    # We need to override the fee to 3_000 to cover inner transactions
    # App clients don't yet support "extra_fees" like other tranasctions, so we need to do it manually
    sp_call = digital_marketplace_client.algod_client.suggested_params()
    sp_call.flat_fee = True
    sp_call.fee = 3_000
    result = digital_marketplace_client.delete_delete_application(
        transaction_parameters=algokit_utils.TransactionParameters(
            suggested_params=sp_call,
            # this call transfers the asset so it must be in the foreign array
            foreign_assets=[test_asset_id]
        ),
    )

    # ensure the call is confirmed
    assert result.confirmed_round

    # get the creators balance after deletion
    after_call_amount = algorand.account.get_information(
        creator.address
    )["amount"]

    # ensure the creator gets all of the assets and ALGO in the app
    assert after_call_amount - before_call_amount == 6_600_000 + 200_000 - 3_000
    assert (
        algorand.account.get_asset_information(
            creator.address, test_asset_id
        )["asset-holding"]["amount"]
        == 8
    )
