<template>
  <UCard :ui="{ root: 'ring-0 border border-neutral-200 !bg-white shadow-sm' }">
    <div class="flex items-start justify-between gap-4">
      <div>
        <p class="text-sm font-medium text-neutral-500">{{ label }}</p>
        <p class="mt-2 text-3xl font-semibold tracking-tight text-neutral-950">{{ value }}</p>
        <p class="mt-2 text-xs text-neutral-500">{{ detail }}</p>
      </div>
      <div class="flex size-10 items-center justify-center rounded-xl bg-yellow-100 text-yellow-800">
        <UIcon :name="icon" class="size-5" />
      </div>
    </div>
  </UCard>
</template>

<script setup lang="ts">
defineProps<{
  label: string;
  value: string;
  detail: string;
  icon: string;
}>();
</script>
