from copy import deepcopy

import algokit_utils
import algosdk.error
import pytest
from algokit_utils import get_localnet_default_account
from algokit_utils.config import config
from algosdk.atomic_transaction_composer import TransactionWithSigner
from algosdk.transaction import (
    AssetCreateTxn,
    AssetTransferTxn,
    PaymentTxn,
    wait_for_confirmation,
)
from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient

from smart_contracts.artifacts.digital_marketplace.client import (
    DigitalMarketplaceClient,
)


@pytest.fixture(scope="session")
def test_asset_id(algod_client: AlgodClient) -> int:
    account = get_localnet_default_account(algod_client)
    sent_txn = wait_for_confirmation(
        algod_client,
        algod_client.send_transaction(
            AssetCreateTxn(
                sender=account.address,
                sp=algod_client.suggested_params(),
                total=10,
                decimals=0,
                default_frozen=False,
            ).sign(account.private_key)
        ),
    )

    return sent_txn["asset-index"]


@pytest.fixture(scope="session")
def creator(algod_client: AlgodClient) -> algokit_utils.Account:
    return get_localnet_default_account(algod_client)


@pytest.fixture(scope="session")
def digital_marketplace_client(
    test_asset_id: int,
    creator: algokit_utils.Account,
    algod_client: AlgodClient,
    indexer_client: IndexerClient,
) -> DigitalMarketplaceClient:
    config.configure(
        debug=True,
        # trace_all=True,
    )

    client = DigitalMarketplaceClient(
        algod_client,
        creator=creator,
        indexer_client=indexer_client,
    )

    client.create_create_application(asset_to_sell=test_asset_id)
    return client


def test_prepare_deposit(
    digital_marketplace_client: DigitalMarketplaceClient,
    creator: algokit_utils.Account,
    test_asset_id: int,
) -> None:
    pytest.raises(
        algosdk.error.AlgodHTTPError,
        lambda: digital_marketplace_client.algod_client.account_asset_info(
            digital_marketplace_client.app_address, test_asset_id
        ),
    )

    sp_pay = digital_marketplace_client.algod_client.suggested_params()
    sp_call = deepcopy(sp_pay)
    sp_call.flat_fee = True
    sp_call.fee = 2_000

    result = digital_marketplace_client.prepare_deposit(
        mbr_pay=TransactionWithSigner(
            PaymentTxn(
                sender=creator.address,
                sp=sp_pay,
                receiver=digital_marketplace_client.app_address,
                amt=200_000,
            ),
            creator.signer,
        ),
        asset_to_sell=test_asset_id,
        transaction_parameters=algokit_utils.TransactionParameters(
            suggested_params=sp_call,
        ),
    )

    assert result.confirmed_round

    assert (
        digital_marketplace_client.algod_client.account_asset_info(
            digital_marketplace_client.app_address, test_asset_id
        )["asset-holding"]["amount"]
        == 0
    )


def test_deposit(
    digital_marketplace_client: DigitalMarketplaceClient,
    creator: algokit_utils.Account,
    test_asset_id: int,
):
    result = digital_marketplace_client.deposit(
        xfer=TransactionWithSigner(
            AssetTransferTxn(
                index=test_asset_id,
                sender=creator.address,
                receiver=digital_marketplace_client.app_address,
                amt=3,
                sp=digital_marketplace_client.algod_client.suggested_params(),
            ),
            creator.signer,
        )
    )

    assert result.confirmed_round

    assert (
        digital_marketplace_client.algod_client.account_asset_info(
            digital_marketplace_client.app_address, test_asset_id
        )["asset-holding"]["amount"]
        == 3
    )


def test_set_price(digital_marketplace_client: DigitalMarketplaceClient):
    result = digital_marketplace_client.set_price(unitary_price=3_300_000)

    assert result.confirmed_round


def test_buy(digital_marketplace_client: DigitalMarketplaceClient, test_asset_id: int):
    test_account = algokit_utils.get_account(
        digital_marketplace_client.algod_client, "test_account", 100
    )

    wait_for_confirmation(
        digital_marketplace_client.algod_client,
        digital_marketplace_client.algod_client.send_transaction(
            AssetTransferTxn(
                index=test_asset_id,
                sender=test_account.address,
                receiver=test_account.address,
                amt=0,
                sp=digital_marketplace_client.algod_client.suggested_params(),
            ).sign(test_account.signer.private_key)
        ),
    )

    sp_pay = digital_marketplace_client.algod_client.suggested_params()
    sp_call = deepcopy(sp_pay)
    sp_call.flat_fee = True
    sp_call.fee = 2_000
    result = digital_marketplace_client.buy(
        buyer_txn=TransactionWithSigner(
            PaymentTxn(
                sender=test_account.address,
                receiver=digital_marketplace_client.app_address,
                amt=6_600_000,
                sp=digital_marketplace_client.algod_client.suggested_params(),
            ),
            test_account.signer,
        ),
        quantity=2,
        asset_to_buy=test_asset_id,
        transaction_parameters=algokit_utils.TransactionParameters(
            sender=test_account.address,
            signer=test_account.signer,
            suggested_params=sp_call,
        ),
    )

    assert result.confirmed_round


def test_withdraw(
    digital_marketplace_client: DigitalMarketplaceClient,
    creator: algokit_utils.Account,
    test_asset_id: int,
):
    before_call_amount = digital_marketplace_client.algod_client.account_info(
        creator.address
    )["amount"]

    sp_call = digital_marketplace_client.algod_client.suggested_params()
    sp_call.flat_fee = True
    sp_call.fee = 3_000
    result = digital_marketplace_client.delete_withdraw(
        asset_to_withdraw=test_asset_id,
        transaction_parameters=algokit_utils.TransactionParameters(
            suggested_params=sp_call
        ),
    )

    assert result.confirmed_round

    after_call_amount = digital_marketplace_client.algod_client.account_info(
        creator.address
    )["amount"]

    assert after_call_amount - before_call_amount == 6_600_000 + 200_000 - 3_000
    assert (
        digital_marketplace_client.algod_client.account_asset_info(
            creator.address, test_asset_id
        )["asset-holding"]["amount"]
        == 8
    )
