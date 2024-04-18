import * as algokit from '@algorandfoundation/algokit-utils'
import { DigitalMarketplaceClient } from './contracts/DigitalMarketplace'

/**
 * Create the application and opt it into the desired asset
 */
export function create(
  algorand: algokit.AlgorandClient,
  dmClient: DigitalMarketplaceClient,
  sender: string,
  unitaryPrice: bigint,
  quantity: bigint,
  assetBeingSold: bigint,
  setAppId: (id: number) => void,
) {
  return async () => {
    let assetId = assetBeingSold

    if (assetId === 0n) {
      const assetCreate = await algorand.send.assetCreate({
        sender,
        total: quantity,
      })

      assetId = BigInt(assetCreate.confirmation.assetIndex!)
    }

    const createResult = await dmClient.create.createApplication({ assetId, unitaryPrice })

    const mbrTxn = await algorand.transactions.payment({
      sender,
      receiver: createResult.appAddress,
      amount: algokit.algos(0.1 + 0.1),
      extraFee: algokit.algos(0.001),
    })

    await dmClient.optInToAsset({ mbrPay: mbrTxn })

    await algorand.send.assetTransfer({
      assetId,
      sender,
      receiver: createResult.appAddress,
      amount: quantity,
    })

    setAppId(Number(createResult.appId))
  }
}

export function buy(
  algorand: algokit.AlgorandClient,
  dmClient: DigitalMarketplaceClient,
  sender: string,
  appAddress: string,
  quantity: bigint,
  unitaryPrice: bigint,
  setUnitsLeft: React.Dispatch<React.SetStateAction<bigint>>,
) {
  return async () => {
    const buyerTxn = await algorand.transactions.payment({
      sender,
      receiver: appAddress,
      amount: algokit.microAlgos(Number(quantity * unitaryPrice)),
      extraFee: algokit.algos(0.001),
    })

    await dmClient.buy({
      buyerTxn,
      quantity,
    })

    const state = await dmClient.getGlobalState()
    const info = await algorand.account.getAssetInformation(appAddress, state.assetId!.asBigInt())
    setUnitsLeft(info.balance)
  }
}

export function deleteApp(dmClient: DigitalMarketplaceClient, setAppId: (id: number) => void) {
  return async () => {
    await dmClient.delete.deleteApplication({}, { sendParams: { fee: algokit.algos(0.003) } })
    setAppId(0)
  }
}
