import { type BigNumber } from '@rotki/common';
import { LpType } from '@rotki/common/lib/defi';

export const useLiquidityPosition = () => {
  const { uniswapV2Balances, uniswapV3Balances } = useUniswapStore();
  const { balanceList: sushiswapBalances } = useSushiswapStore();
  const { balancerBalances } = useBalancerStore();
  const { assetSymbol } = useAssetInfoRetrieval();

  const lpAggregatedBalances = (includeNft = true) =>
    computed(() => {
      const mappedUniswapV3Balances = get(uniswapV3Balances([])).map(item => ({
        ...item,
        usdValue: item.userBalance.usdValue,
        asset: item.nftId,
        premiumOnly: true,
        type: 'nft',
        lpType: LpType.UNISWAP_V3
      }));

      const mappedUniswapV2Balances = get(uniswapV2Balances([])).map(item => ({
        ...item,
        usdValue: item.userBalance.usdValue,
        asset: createEvmIdentifierFromAddress(item.address),
        premiumOnly: false,
        type: 'token',
        lpType: LpType.UNISWAP_V2
      }));

      const mappedSushiswapBalances = get(sushiswapBalances([])).map(item => ({
        ...item,
        usdValue: item.userBalance.usdValue,
        asset: createEvmIdentifierFromAddress(item.address),
        premiumOnly: true,
        type: 'token',
        lpType: LpType.SUSHISWAP
      }));

      const mappedBalancerBalances = get(balancerBalances([])).map(item => ({
        ...item,
        usdValue: item.userBalance.usdValue as BigNumber,
        asset: createEvmIdentifierFromAddress(item.address),
        premiumOnly: true,
        assets: item.tokens.map(asset => ({
          ...asset,
          asset: asset.token
        })),
        type: 'token',
        lpType: LpType.BALANCER
      }));

      return [
        ...(includeNft ? mappedUniswapV3Balances : []),
        ...mappedUniswapV2Balances,
        ...mappedSushiswapBalances,
        ...mappedBalancerBalances
      ]
        .sort((a, b) => sortDesc(a.usdValue, b.usdValue))
        .map((item, id) => ({ ...item, id }));
    });

  const lpTotal = (includeNft = false) =>
    computed<BigNumber>(() =>
      bigNumberSum(
        get(lpAggregatedBalances(includeNft)).map(item => item.usdValue)
      )
    );

  const getPoolName = (type: LpType, assets: string[]) => {
    const concatAssets = (assets: string[]) =>
      assets.map(asset => get(assetSymbol(asset))).join('/');

    const data = [
      {
        identifier: LpType.UNISWAP_V2,
        name: (assets: string[]) => `UNIv2 ${concatAssets(assets)}`
      },
      {
        identifier: LpType.UNISWAP_V3,
        name: (assets: string[]) => `UNIv3 ${concatAssets(assets)}`
      },
      {
        identifier: LpType.SUSHISWAP,
        name: (assets: string[]) => `SLP ${concatAssets(assets)}`
      },
      {
        identifier: LpType.BALANCER,
        name: (assets: string[]) => concatAssets(assets)
      }
    ];

    const selected = data.find(({ identifier }) => identifier === get(type));

    if (!selected) {
      return concatAssets(assets);
    }

    return selected.name(get(assets));
  };

  return {
    lpAggregatedBalances,
    lpTotal,
    getPoolName
  };
};
