<template>
  <main class="space-y-6 p-6 lg:p-8">
    <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <p class="text-sm font-medium text-yellow-700">Commercial workspace</p>
        <h1 class="mt-1 text-3xl font-semibold tracking-tight text-neutral-950">
          Proposals
        </h1>
        <p class="mt-2 text-neutral-500">
          AI-drafted proposals awaiting review, approval, or client response.
        </p>
      </div>
      <UButton
        to="/kora-ai"
        icon="i-lucide-sparkles"
        class="bg-[#e0b818] font-semibold text-black hover:bg-yellow-400"
        >Generate proposal</UButton
      >
    </div>
    <div class="grid gap-4 sm:grid-cols-3">
      <MetricCard
        label="In review"
        value="7"
        detail="KES 4.2M total"
        icon="i-lucide-search-check"
      /><MetricCard
        label="Approved"
        value="4"
        detail="Ready to send"
        icon="i-lucide-badge-check"
      /><MetricCard
        label="Accepted"
        value="12"
        detail="This quarter"
        icon="i-lucide-party-popper"
      />
    </div>
    <DataTable :columns="columns" :rows="proposals" row-key="id"
      ><template #cell-client="{ row }"
        ><div>
          <p class="font-medium text-neutral-900">{{ row.client }}</p>
          <p class="text-xs text-neutral-500">{{ row.company }}</p>
        </div></template
      ><template #cell-status="{ row }"
        ><UBadge
          :color="
            row.status === 'Accepted'
              ? 'success'
              : row.status === 'In review'
                ? 'warning'
                : 'neutral'
          "
          variant="subtle"
          >{{ row.status }}</UBadge
        ></template
      ><template #cell-action="{ row }"
        ><UButton
          :to="`/proposals/${row.id}`"
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
  { key: "name", label: "Proposal" },
  { key: "client", label: "Client" },
  { key: "value", label: "Value" },
  { key: "owner", label: "Owner" },
  { key: "status", label: "Status" },
  { key: "updated", label: "Updated" },
  { key: "action", label: "" },
];
const proposals = [
  {
    id: 1,
    name: "Experience redesign",
    client: "Amina Njeri",
    company: "Mawingu Retail",
    value: "KES 820,000",
    owner: "Mercy W.",
    status: "In review",
    updated: "Today",
  },
  {
    id: 2,
    name: "Fleet visibility platform",
    client: "David Otieno",
    company: "Nuru Logistics",
    value: "KES 1,250,000",
    owner: "Brian K.",
    status: "Approved",
    updated: "Jul 20",
  },
  {
    id: 3,
    name: "Patient portal discovery",
    client: "Lina Wanjiku",
    company: "Cedar Health",
    value: "KES 640,000",
    owner: "Mercy W.",
    status: "Accepted",
    updated: "Jul 18",
  },
];
</script>
