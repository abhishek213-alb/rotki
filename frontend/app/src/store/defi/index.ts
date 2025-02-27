import { type DefiAccount } from '@rotki/common/lib/account';
import { Blockchain, DefiProtocol } from '@rotki/common/lib/blockchain';
import { type ComputedRef } from 'vue';
import { AllDefiProtocols } from '@/types/defi/overview';
import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { ProtocolVersion } from '@/types/defi';
import {
  ALL_DECENTRALIZED_EXCHANGES,
  ALL_MODULES
} from '@/types/session/purge';

type ResetStateParams =
  | Module
  | typeof ALL_MODULES
  | typeof ALL_DECENTRALIZED_EXCHANGES;

export const useDefiStore = defineStore('defi', () => {
  const allProtocols: Ref<AllDefiProtocols> = ref({});

  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const premium = usePremium();

  const liquityStore = useLiquityStore();
  const yearnStore = useYearnStore();
  const aaveStore = useAaveStore();
  const compoundStore = useCompoundStore();
  const makerDaoStore = useMakerDaoStore();
  const balancerStore = useBalancerStore();
  const sushiswapStore = useSushiswapStore();
  const uniswapStore = useUniswapStore();
  const { t } = useI18n();

  const { fetchAllDefi: fetchAllDefiCaller } = useDefiApi();

  const { addressesV1: yearnV1Addresses, addressesV2: yearnV2Addresses } =
    storeToRefs(yearnStore);
  const { addresses: aaveAddresses } = storeToRefs(aaveStore);
  const { addresses: compoundAddresses } = storeToRefs(compoundStore);
  const { addresses: makerDaoAddresses } = storeToRefs(makerDaoStore);

  type DefiProtocols = Exclude<
    DefiProtocol,
    DefiProtocol.MAKERDAO_VAULTS | DefiProtocol.UNISWAP | DefiProtocol.LIQUITY
  >;

  const defiAccounts = (
    protocols: DefiProtocol[]
  ): ComputedRef<DefiAccount[]> =>
    computed(() => {
      const addresses: {
        [key in DefiProtocols]: string[];
      } = {
        [DefiProtocol.MAKERDAO_DSR]: [],
        [DefiProtocol.AAVE]: [],
        [DefiProtocol.COMPOUND]: [],
        [DefiProtocol.YEARN_VAULTS]: [],
        [DefiProtocol.YEARN_VAULTS_V2]: []
      };

      const noProtocolsSelected = protocols.length === 0;

      if (
        noProtocolsSelected ||
        protocols.includes(DefiProtocol.MAKERDAO_DSR)
      ) {
        addresses[DefiProtocol.MAKERDAO_DSR] = get(makerDaoAddresses);
      }

      if (noProtocolsSelected || protocols.includes(DefiProtocol.AAVE)) {
        addresses[DefiProtocol.AAVE] = get(aaveAddresses);
      }

      if (noProtocolsSelected || protocols.includes(DefiProtocol.COMPOUND)) {
        addresses[DefiProtocol.COMPOUND] = get(compoundAddresses);
      }

      if (
        noProtocolsSelected ||
        protocols.includes(DefiProtocol.YEARN_VAULTS)
      ) {
        addresses[DefiProtocol.YEARN_VAULTS] = get(yearnV1Addresses);
      }

      if (
        noProtocolsSelected ||
        protocols.includes(DefiProtocol.YEARN_VAULTS_V2)
      ) {
        addresses[DefiProtocol.YEARN_VAULTS_V2] = get(yearnV2Addresses);
      }

      const accounts: Record<string, DefiAccount> = {};
      for (const protocol in addresses) {
        const selectedProtocol = protocol as DefiProtocols;
        const perProtocolAddresses = addresses[selectedProtocol];
        for (const address of perProtocolAddresses) {
          if (accounts[address]) {
            accounts[address].protocols.push(selectedProtocol);
          } else {
            accounts[address] = {
              address,
              chain: Blockchain.ETH,
              protocols: [selectedProtocol]
            };
          }
        }
      }

      return Object.values(accounts);
    });

  const { setStatus, fetchDisabled } = useStatusUpdater(Section.DEFI_BALANCES);

  const fetchDefiBalances = async (refresh: boolean) => {
    if (fetchDisabled(refresh)) {
      return;
    }

    setStatus(Status.LOADING);
    try {
      const taskType = TaskType.DEFI_BALANCES;
      const { taskId } = await fetchAllDefiCaller();
      const { result } = await awaitTask<AllDefiProtocols, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.defi.balances.task.title')
        }
      );

      set(allProtocols, AllDefiProtocols.parse(result));
    } catch (e: any) {
      const title = t('actions.defi.balances.error.title');
      const message = t('actions.defi.balances.error.description', {
        error: e.message
      });
      notify({
        title,
        message,
        display: true
      });
    }
    setStatus(Status.LOADED);
  };

  async function fetchAllDefi(refresh = false) {
    const section = Section.DEFI_OVERVIEW;

    if (fetchDisabled(refresh, section)) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section);
    await fetchDefiBalances(refresh);
    setStatus(Status.PARTIALLY_LOADED, section);

    await Promise.allSettled([
      aaveStore.fetchBalances(refresh),
      makerDaoStore.fetchDSRBalances(refresh),
      makerDaoStore.fetchMakerDAOVaults(refresh),
      compoundStore.fetchBalances(refresh),
      yearnStore.fetchBalances({
        refresh,
        version: ProtocolVersion.V1
      }),
      yearnStore.fetchBalances({
        refresh,
        version: ProtocolVersion.V2
      }),
      liquityStore.fetchBalances(refresh)
    ]);

    setStatus(Status.LOADED, section);
  }

  const modules: Record<string, () => void> = {
    [Module.MAKERDAO_DSR]: () => makerDaoStore.reset(Module.MAKERDAO_DSR),
    [Module.MAKERDAO_VAULTS]: () => makerDaoStore.reset(Module.MAKERDAO_VAULTS),
    [Module.AAVE]: () => aaveStore.reset(),
    [Module.COMPOUND]: () => compoundStore.reset(),
    [Module.YEARN]: () => yearnStore.reset(ProtocolVersion.V1),
    [Module.YEARN_V2]: () => yearnStore.reset(ProtocolVersion.V2),
    [Module.UNISWAP]: () => uniswapStore.reset(),
    [Module.SUSHISWAP]: () => sushiswapStore.reset(),
    [Module.BALANCER]: () => balancerStore.reset(),
    [Module.LIQUITY]: () => liquityStore.reset()
  };

  const resetState = (module: ResetStateParams) => {
    if (module === ALL_DECENTRALIZED_EXCHANGES) {
      [Module.UNISWAP, Module.SUSHISWAP, Module.BALANCER].map(mod =>
        modules[mod]()
      );
    } else if (module === ALL_MODULES) {
      for (const mod in modules) {
        modules[mod as Module]();
      }
    } else {
      const reset = modules[module];

      if (!reset) {
        logger.warn(`Missing reset function for ${module}`);
      } else {
        reset();
      }
    }
  };

  const reset = () => {
    set(allProtocols, {});
    resetState(ALL_MODULES);
  };

  watch(premium, premium => {
    if (!premium) {
      reset();
    }
  });

  return {
    allProtocols,
    defiAccounts,
    fetchDefiBalances,
    fetchAllDefi,
    resetState,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useDefiStore, import.meta.hot));
}
