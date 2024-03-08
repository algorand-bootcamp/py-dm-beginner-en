import puyapy as pup
from puyapy import arc4


class DigitalMarketplace(arc4.ARC4Contract):
    asset_id: pup.GlobalState[pup.UInt64]
    deposited: pup.GlobalState[pup.UInt64]
    unitary_price: pup.GlobalState[pup.UInt64]

    @arc4.abimethod(allow_actions=["NoOp"], create=True)
    def create_application(self, asset_to_sell: pup.Asset) -> None:
        self.asset_id.value = asset_to_sell.asset_id
        self.deposited.value = pup.UInt64(0)
        self.unitary_price.value = pup.UInt64(0)

    @arc4.abimethod
    def prepare_deposit(
        self, mbr_pay: pup.gtxn.PaymentTransaction, asset_to_sell: pup.Asset
    ) -> None:
        assert pup.Txn.sender == pup.Global.creator_address
        _balance, opted_into = pup.op.AssetHoldingGet.asset_balance(
            pup.Global.current_application_address, self.asset_id.value
        )
        assert not opted_into

        assert mbr_pay.receiver == pup.Global.current_application_address
        assert (
            mbr_pay.amount
            == pup.Global.min_balance + pup.Global.asset_opt_in_min_balance
        )
        assert mbr_pay.close_remainder_to == pup.Global.zero_address
        assert mbr_pay.rekey_to == pup.Global.zero_address

        pup.itxn.AssetTransfer(
            xfer_asset=self.asset_id.value,
            asset_receiver=pup.Global.current_application_address,
            asset_amount=0,
        ).submit()

    @arc4.abimethod
    def deposit(self, xfer: pup.gtxn.AssetTransferTransaction) -> None:
        assert xfer.xfer_asset.asset_id == self.asset_id.value
        assert xfer.asset_receiver == pup.Global.current_application_address
        assert xfer.asset_close_to == pup.Global.zero_address
        assert xfer.rekey_to == pup.Global.zero_address

        self.deposited.value += xfer.asset_amount

    @arc4.abimethod(allow_actions=["DeleteApplication"])
    def withdraw(self, asset_to_withdraw: pup.Asset) -> None:
        assert pup.Txn.sender == pup.Global.creator_address

        pup.itxn.AssetTransfer(
            xfer_asset=self.asset_id.value,
            asset_receiver=pup.Global.creator_address,
            asset_amount=0,
            asset_close_to=pup.Global.creator_address,
        ).submit()

        pup.itxn.Payment(
            receiver=pup.Global.creator_address,
            amount=0,
            close_remainder_to=pup.Global.creator_address,
        ).submit()

    @arc4.abimethod
    def set_price(self, unitary_price: arc4.UInt64) -> None:
        assert pup.Txn.sender == pup.Global.creator_address

        self.unitary_price.value = unitary_price.decode()

    @arc4.abimethod
    def buy(
        self,
        buyer_txn: pup.gtxn.PaymentTransaction,
        quantity: arc4.UInt64,
        asset_to_buy: pup.Asset,
    ) -> None:
        decoded_quantity = quantity.decode()
        assert buyer_txn.sender == pup.Txn.sender
        assert buyer_txn.receiver == pup.Global.current_application_address
        assert buyer_txn.amount == self.unitary_price.value * decoded_quantity
        assert buyer_txn.close_remainder_to == pup.Global.zero_address
        assert buyer_txn.rekey_to == pup.Global.zero_address

        pup.itxn.AssetTransfer(
            xfer_asset=self.asset_id.value,
            asset_receiver=pup.Txn.sender,
            asset_amount=decoded_quantity,
        ).submit()

        self.deposited.value -= decoded_quantity
