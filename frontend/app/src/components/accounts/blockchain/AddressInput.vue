<script setup lang="ts">
import { helpers, requiredIf } from '@vuelidate/validators';
import { isEmpty } from 'lodash-es';
import { toMessages } from '@/utils/validation';

const props = withDefaults(
  defineProps<{
    addresses: string[];
    disabled: boolean;
    multi: boolean;
    errorMessages?: string[];
  }>(),
  {
    errorMessages: () => []
  }
);

const emit = defineEmits<{
  (e: 'update:addresses', addresses: string[]): void;
}>();

const { t } = useI18n();
const { errorMessages, addresses, disabled } = toRefs(props);
const address = ref('');
const userAddresses = ref('');
const multiple = ref(false);
const entries = computed(() => {
  const allAddresses = get(userAddresses)
    .split(',')
    .map(value => value.trim())
    .filter(entry => entry.length > 0);

  const entries: Record<string, string> = {};
  for (const address of allAddresses) {
    const lowerCase = address.toLocaleLowerCase();
    if (entries[lowerCase]) {
      continue;
    }
    entries[lowerCase] = address;
  }
  return Object.values(entries);
});

watch(multiple, () => {
  set(userAddresses, '');
});

const onPasteMulti = (event: ClipboardEvent) => {
  if (get(disabled)) {
    return;
  }
  const paste = trimOnPaste(event);
  if (paste) {
    userAddresses.value += paste.replace(/,(0x)/g, ',\n0x');
  }
};

const onPasteAddress = (event: ClipboardEvent) => {
  if (get(disabled)) {
    return;
  }
  const paste = trimOnPaste(event);
  if (paste) {
    set(address, paste);
  }
};

const updateAddresses = (addresses: string[]) => {
  emit('update:addresses', addresses);
};

watch(entries, addresses => updateAddresses(addresses));
watch(address, address => {
  updateAddresses(address ? [address.trim()] : []);
});

const setAddress = (addresses: string[]) => {
  if (addresses.length === 1) {
    set(address, addresses[0]);
  }
};

watch(addresses, addresses => setAddress(addresses));
onMounted(() => setAddress(get(addresses)));

const rules = {
  address: {
    required: helpers.withMessage(
      t('account_form.validation.address_non_empty').toString(),
      requiredIf(logicNot(multiple))
    )
  },
  userAddresses: {
    required: helpers.withMessage(
      t('account_form.validation.address_non_empty').toString(),
      requiredIf(logicAnd(multiple))
    )
  }
};

const { setValidation } = useAccountDialog();

const v$ = setValidation(
  rules,
  {
    address,
    userAddresses
  },
  {
    $autoDirty: true,
    $stopPropagation: true,
    $externalResults: computed(() => ({
      address: get(errorMessages)
    }))
  }
);

watch(errorMessages, errors => {
  if (!isEmpty(errors)) {
    get(v$).$validate();
  }
});
</script>

<template>
  <div>
    <RuiCheckbox
      v-if="multi"
      v-model="multiple"
      color="primary"
      class="mt-0 mb-6"
      hide-details
      :disabled="disabled"
    >
      {{ t('account_form.labels.multiple') }}
    </RuiCheckbox>
    <RuiTextField
      v-if="!multiple"
      v-model="address"
      data-cy="account-address-field"
      variant="outlined"
      color="primary"
      class="account-form__address"
      :label="t('common.account')"
      :rules="rules"
      autocomplete="off"
      :disabled="disabled"
      :error-messages="toMessages(v$.address)"
      @paste="onPasteAddress($event)"
      @blur="v$.address.$touch()"
    />
    <VTextarea
      v-else
      v-model="userAddresses"
      outlined
      :disabled="disabled"
      :error-messages="toMessages(v$.userAddresses)"
      :hint="t('account_form.labels.addresses_hint')"
      :label="t('account_form.labels.addresses')"
      @blur="v$.userAddresses.$touch()"
      @paste="onPasteMulti($event)"
    />
    <div v-if="multiple">
      <div
        class="text-caption mb-2"
        v-text="
          t(
            'account_form.labels.addresses_entries',
            {
              count: entries.length
            },
            entries.length
          )
        "
      />
    </div>
  </div>
</template>
