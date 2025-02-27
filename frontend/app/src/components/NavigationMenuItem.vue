<script setup lang="ts">
import { type VueConstructor } from 'vue';

withDefaults(
  defineProps<{
    showTooltips?: boolean;
    icon?: string;
    text: string;
    image?: string;
    iconComponent?: VueConstructor | null;
    active?: boolean;
    subMenu?: boolean;
  }>(),
  {
    showTooltips: false,
    icon: '',
    image: '',
    iconComponent: null,
    active: false,
    subMenu: false
  }
);

const { dark } = useTheme();

const css = useCssModule();
</script>

<template>
  <div class="flex grow">
    <VTooltip v-if="showTooltips" right>
      <template #activator="{ on }">
        <VListItemIcon :class="subMenu ? 'my-2 mr-2' : 'my-3 mr-3'" v-on="on">
          <VImg
            v-if="image"
            contain
            width="24px"
            :src="image"
            class="nav-icon"
            :class="{
              [css.image]: true,
              [css['image--inverted']]: dark
            }"
          />
          <Component
            :is="iconComponent"
            v-else-if="iconComponent"
            :active="active"
          />
          <RuiIcon v-else :name="icon" />
        </VListItemIcon>
      </template>
      <span>{{ text }}</span>
    </VTooltip>
    <VListItemIcon v-else :class="subMenu ? 'my-2 mr-2' : 'my-3 mr-3'">
      <VImg
        v-if="image"
        contain
        width="24px"
        :src="image"
        class="nav-icon"
        :class="{
          [css.image]: true,
          [css['image--inverted']]: dark
        }"
      />
      <Component
        :is="iconComponent"
        v-else-if="iconComponent"
        :active="active"
      />
      <RuiIcon v-else :name="icon" />
    </VListItemIcon>
    <VListItemContent class="flex grow py-0 text-capitalize">
      <VListItemTitle :class="{ 'text-sm': subMenu }">
        {{ text }}
      </VListItemTitle>
    </VListItemContent>
  </div>
</template>

<style module lang="scss">
.image {
  opacity: 0.7;
  filter: brightness(0);

  &--inverted {
    opacity: 1;
    filter: brightness(0) invert(100%);
  }
}
</style>
