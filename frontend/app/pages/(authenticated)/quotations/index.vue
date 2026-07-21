<template>
  <main class="space-y-6 p-6 lg:p-8">
    <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <p class="text-sm font-medium text-yellow-700">Commercial workspace</p>
        <h1 class="mt-1 text-3xl font-semibold tracking-tight text-neutral-950">
          Quotations
        </h1>
        <p class="mt-2 text-neutral-500">
          Track values, expiry dates, and client acceptance in one place.
        </p>
      </div>
      <UButton
        to="/kora-ai"
        icon="i-lucide-plus"
        class="bg-[#e0b818] font-semibold text-black hover:bg-yellow-400"
        >New quotation</UButton
      >
    </div>
    <DataTable :columns="columns" :rows="quotes" row-key="id"
      ><template #cell-status="{ row }"
        ><UBadge
          :color="
            row.status === 'Accepted'
              ? 'success'
              : row.status === 'Sent'
                ? 'warning'
                : 'neutral'
          "
          variant="subtle"
          >{{ row.status }}</UBadge
        ></template
      ><template #cell-action="{ row }"
        ><UButton
          :to="`/quotes/${row.id}`"
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
  { key: "number", label: "Quote" },
  { key: "client", label: "Client" },
  { key: "proposal", label: "Proposal" },
  { key: "amount", label: "Amount" },
  { key: "expires", label: "Expires" },
  { key: "status", label: "Status" },
  { key: "action", label: "" },
];
const quotes = [
  {
    id: 1,
    number: "QT-1024",
    client: "Mawingu Retail",
    proposal: "Experience redesign",
    amount: "KES 820,000",
    expires: "Aug 18, 2026",
    status: "Draft",
  },
  {
    id: 2,
    number: "QT-1023",
    client: "Nuru Logistics",
    proposal: "Fleet visibility platform",
    amount: "KES 1,250,000",
    expires: "Aug 12, 2026",
    status: "Sent",
  },
  {
    id: 3,
    number: "QT-1018",
    client: "Cedar Health",
    proposal: "Patient portal discovery",
    amount: "KES 640,000",
    expires: "Jul 30, 2026",
    status: "Accepted",
  },
];
</script>
