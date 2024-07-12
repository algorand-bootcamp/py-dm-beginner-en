# pyright: reportMissingModuleSource=false
from algopy import (
    # On Algorand, assets are native objects rather than smart contracts
    Asset,
    # Global is used to access global variables from the network
    Global,
    # Txn is used access information about the current transcation
    Txn,
    # By default, all numbers in the AVM are 64-bit unsigned integers
    UInt64,
    # ARC4 defines the Algorand ABI for method calling and type encoding
    arc4,
    # gtxn is used to read transaction within the same atomic group
    gtxn,
    # itxn is used to send transactions from within a smart contract
    itxn,
)


# We want the methods in our contract to follow the ARC4 standard
class DigitalMarketplace(arc4.ARC4Contract):
    # Every asset has a unique ID
    # We want to store the ID for the asset we are selling
    asset_id: UInt64

    # We want to store the price for the asset we are selling
    unitary_price: UInt64

    # We want create_application to be a plublic ABI method
    @arc4.abimethod(
        # There are certain actions that a contract call can do
        # Some examples are UpdateApplication, DeleteApplication, and NoOp
        # NoOp is a call that does nothing special after it is exected
        allow_actions=["NoOp"],
        # Require that this method is only callable when creating the app
        create="require",
    )
    def create_application(
        self,
        # The ID of the asset we're selling
        asset_id: Asset,
        # The initial sale price
        unitary_price: UInt64,
    ) -> None:
        # Save the values we passed in to our method in the contract's state
        self.asset_id = asset_id.id
        self.unitary_price = unitary_price
