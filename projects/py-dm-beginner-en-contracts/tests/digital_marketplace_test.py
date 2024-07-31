from collections.abc import Generator

import algopy
import pytest
from algopy_testing import AlgopyTestContext, algopy_testing_context

from smart_contracts.digital_marketplace.contract import DigitalMarketplace


@pytest.fixture()
def context() -> Generator[AlgopyTestContext, None, None]:
    with algopy_testing_context() as ctx:
        yield ctx
        ctx.reset()


def test_create_application(context: AlgopyTestContext) -> None:
    # Arrange
    test_asset = context.any_asset()
    test_uint = context.any_uint64()
    contract = DigitalMarketplace()

    # Act
    contract.create_application(test_asset, test_uint)

    # Assert
    assert contract.asset_id == test_asset.id
    assert contract.unitary_price == test_uint


def test_opt_in_to_asset(context: AlgopyTestContext) -> None:
    # Arrange
    test_app_address = context.any_account()
    test_pay_txn = context.any_payment_transaction(
        receiver=test_app_address, amount=algopy.UInt64(200_000)
    )
    context.patch_global_fields(
        current_application_address=test_app_address,
        min_balance=algopy.UInt64(100_000),
        asset_opt_in_min_balance=algopy.UInt64(100_000),
    )
    contract = DigitalMarketplace()
    contract.asset_id = context.any_asset().id

    # Act
    contract.opt_in_to_asset(test_pay_txn)

    # Assert
    last_itxn = context.last_submitted_itxn.asset_transfer
    assert last_itxn.asset_amount == 0
    assert last_itxn.asset_receiver == test_app_address
    assert last_itxn.xfer_asset == contract.asset_id
