<template>
  <main class="space-y-6 p-6 lg:p-8">
    <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <p class="text-sm font-medium text-yellow-700">Meeting intelligence</p>
        <h1 class="mt-1 text-3xl font-semibold tracking-tight text-neutral-950">
          Summaries
        </h1>
        <p class="mt-2 text-neutral-500">
          Structured outputs from discovery and internal strategy meetings.
        </p>
      </div>
      <UButton
        to="/kora-ai"
        icon="i-lucide-upload"
        class="bg-[#e0b818] font-semibold text-black hover:bg-yellow-400"
        >Process transcript</UButton
      >
    </div>
    <DataTable :columns="columns" :rows="summaries" row-key="id"
      ><template #cell-type="{ row }"
        ><UBadge
          :color="row.type === 'Strategy' ? 'warning' : 'neutral'"
          variant="subtle"
          >{{ row.type }}</UBadge
        ></template
      ><template #cell-action="{ row }"
        ><UButton
          :to="`/summaries/${row.id}`"
          size="xs"
          color="neutral"
          variant="outline"
          >View</UButton
        ></template
      ></DataTable
    >
  </main>
</template>
<script setup lang="ts">
const columns = [
  { key: "title", label: "Meeting summary" },
  { key: "client", label: "Client" },
  { key: "type", label: "Meeting type" },
  { key: "owner", label: "Processed by" },
  { key: "date", label: "Created" },
  { key: "action", label: "" },
];
const summaries = [
  {
    id: 1,
    title: "Holiday campaign discovery",
    client: "Mawingu Retail",
    type: "Discovery",
    owner: "Kora AI",
    date: "Jul 15, 2026",
  },
  {
    id: 2,
    title: "Platform scope & pricing",
    client: "Nuru Logistics",
    type: "Strategy",
    owner: "Kora AI",
    date: "Jul 19, 2026",
  },
  {
    id: 3,
    title: "Patient portal discovery",
    client: "Cedar Health",
    type: "Discovery",
    owner: "Kora AI",
    date: "Jul 18, 2026",
  },
];
</script>
