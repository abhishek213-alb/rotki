import { type PremiumCredentialsPayload } from '@/types/session';
import { type ActionStatus } from '@/types/action';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';

export const usePremiumStore = defineStore('session/premium', () => {
  const premium = ref(false);
  const premiumSync = ref(false);
  const componentsReady = ref(false);

  const showComponents = computed(() => get(premium) && get(componentsReady));

  const api = usePremiumCredentialsApi();

  const setup = async ({
    apiKey,
    apiSecret,
    username
  }: PremiumCredentialsPayload): Promise<
    ActionStatus<string | ValidationErrors>
  > => {
    try {
      const success = await api.setPremiumCredentials(
        username,
        apiKey,
        apiSecret
      );

      if (success) {
        set(premium, true);
      }
      return { success };
    } catch (e: any) {
      let errors: string | ValidationErrors = e.message;
      if (e instanceof ApiValidationError) {
        errors = e.getValidationErrors({
          apiKey,
          apiSecret
        });
      }

      return {
        success: false,
        message: errors
      };
    }
  };

  const deletePremium = async (): Promise<ActionStatus> => {
    try {
      const success = await api.deletePremiumCredentials();
      if (success) {
        set(premium, false);
      }
      return { success };
    } catch (e: any) {
      return {
        success: false,
        message: e.message
      };
    }
  };

  return {
    premium,
    premiumSync,
    componentsReady,
    showComponents,
    setup,
    deletePremium
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(usePremiumStore, import.meta.hot));
}
