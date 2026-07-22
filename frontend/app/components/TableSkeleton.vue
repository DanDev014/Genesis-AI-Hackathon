<template>
  <div class="min-w-0 overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm">
    <div class="flex items-center gap-6 border-b border-neutral-200 bg-neutral-50 px-5 py-3">
      <USkeleton v-for="i in columns" :key="i" class="h-3 w-20 bg-neutral-200" />
    </div>
    <div class="divide-y divide-neutral-100">
      <div v-for="i in rows" :key="i" class="flex items-center gap-6 px-5 py-4">
        <USkeleton
          v-for="(width, j) in widths"
          :key="j"
          class="h-4 bg-neutral-200"
          :class="width"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    columns?: number;
    rows?: number;
  }>(),
  {
    columns: 4,
    rows: 6,
  },
);

const pool = ["w-1/4", "w-1/3", "w-20", "w-16", "w-24", "w-28"];

const widths = computed(() =>
  Array.from({ length: props.columns }, (_, i) => pool[i % pool.length]),
);
</script>
