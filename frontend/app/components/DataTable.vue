<template>
  <div class="min-w-0 overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm">
    <div class="overflow-x-auto">
      <table class="min-w-full text-left text-sm">
        <thead class="border-b border-neutral-200 bg-neutral-50 text-xs uppercase tracking-wider text-neutral-500">
          <tr>
            <th v-for="column in columns" :key="column.key" class="whitespace-nowrap px-5 py-3 font-medium">
              {{ column.label }}
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          <tr v-for="(row, index) in rows" :key="row[rowKey] ?? index" class="transition-colors hover:bg-yellow-50/40">
            <td v-for="column in columns" :key="column.key" class="whitespace-nowrap px-5 py-4 text-neutral-700">
              <slot :name="`cell-${column.key}`" :row="row" :value="row[column.key]">
                {{ row[column.key] }}
              </slot>
            </td>
          </tr>
          <tr v-if="rows.length === 0">
            <td :colspan="columns.length" class="px-5 py-12 text-center text-neutral-500">
              {{ emptyText }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  columns: Array<{ key: string; label: string }>;
  rows: Array<Record<string, any>>;
  rowKey?: string;
  emptyText?: string;
}>();
</script>
