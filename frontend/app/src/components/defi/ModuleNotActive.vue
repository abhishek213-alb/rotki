<script setup lang="ts">
import { getCurrentInstance, onMounted, ref } from 'vue';
import { type Module, SUPPORTED_MODULES } from '@/types/modules';
import { Routes } from '@/router/routes';

defineProps<{
  modules: Module[];
}>();

const top = ref(0);

const name = (module: string): string => {
  const data = SUPPORTED_MODULES.find(value => value.identifier === module);
  return data?.name ?? '';
};

const icon = (module: Module): string => {
  const data = SUPPORTED_MODULES.find(value => value.identifier === module);
  return data?.icon ?? '';
};

onMounted(() => {
  const currentInstance = getCurrentInstance();
  assert(currentInstance);
  const $el = currentInstance.proxy.$el;
  const { top: topPoint } = $el.getBoundingClientRect();
  set(top, topPoint);
});

const { t } = useI18n();
</script>

<template>
  <div
    :style="`height: calc(100vh - ${top + 64}px);`"
    class="flex flex-col items-center justify-center"
  >
    <div class="module-not-active__container">
      <VRow align="center" justify="center">
        <VCol v-for="module in modules" :key="module" cols="auto">
          <VImg width="82px" contain :src="icon(module)" />
        </VCol>
      </VRow>
      <VRow align="center" justify="center" class="mt-16">
        <VCol cols="auto" class="text--secondary">
          <i18n
            tag="span"
            path="module_not_active.not_active"
            class="text-center"
          >
            <template #link>
              <InternalLink
                class="module-not-active__link font-weight-regular text-body-1 text-decoration-none"
                :to="Routes.SETTINGS_MODULES"
              >
                {{ t('module_not_active.settings_link') }}
              </InternalLink>
            </template>
            <template #text>
              <div v-if="modules.length > 1">
                {{ t('module_not_active.at_least_one') }}
              </div>
            </template>
            <template #module>
              <span
                v-for="module in modules"
                :key="`mod-${module}`"
                class="module-not-active__module"
              >
                {{ name(module) }}
              </span>
            </template>
          </i18n>
        </VCol>
      </VRow>
    </div>
  </div>
</template>

<style scoped lang="scss">
.module-not-active {
  &__link {
    text-transform: none !important;
  }

  &__container {
    width: 100%;
  }

  &__module {
    &:not(:first-child) {
      &:before {
        content: '& ';
      }
    }
  }
}
</style>
