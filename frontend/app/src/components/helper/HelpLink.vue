﻿<script setup lang="ts">
import { toRefs } from 'vue';

const props = defineProps({
  url: { required: true, type: String },
  tooltip: { required: true, type: String },
  small: { required: false, type: Boolean, default: false }
});

const { url } = toRefs(props);
const { href, onLinkClick } = useLinks(url);
</script>

<template>
  <VTooltip open-delay="400" top>
    <template #activator="{ attrs, on }">
      <VBtn
        icon
        :small="small"
        v-bind="attrs"
        :href="href"
        target="_blank"
        v-on="on"
        @click="onLinkClick()"
      >
        <VIcon :small="small">mdi-help-circle</VIcon>
      </VBtn>
    </template>
    <span>{{ tooltip }}</span>
  </VTooltip>
</template>
