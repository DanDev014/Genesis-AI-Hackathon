<template>
  <main class="space-y-6 p-6 lg:p-8">
    <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <h1 class="mt-1 text-3xl font-semibold tracking-tight text-black">
          Quotations
        </h1>
      </div>
      <UButton to="/kora-ai" icon="i-lucide-plus" class="text-white">
        New quotation
      </UButton>
    </div>

    <div class="flex flex-row gap-3 w-full sm:flex-row">
      <USelect
        v-model="status"
        :items="statuses"
        class="w-full sm:w-48"
        :ui="{
          base: 'bg-white text-neutral-900 ring-neutral-200 focus:ring-2 focus:ring-[#e0b818]',
        }"
        @update:model-value="onFilterChange"
      />
    </div>

    <p v-if="error" class="text-sm text-red-600">
      Couldn't load quotations. Please try again.
    </p>

    <!-- Initial load: no data yet -->
    <TableSkeleton v-if="pending && !data" :columns="4" :rows="8" />

    <!-- Loaded (or refetching) -->
    <div v-else class="relative">
      <div
        v-if="pending"
        class="absolute inset-0 z-10 flex items-center justify-center gap-2 rounded-lg bg-white/70 text-sm text-neutral-500"
      >
        <UIcon name="i-lucide-loader-2" class="size-4 animate-spin" />
        Loading quotations...
      </div>
      <DataTable
        :columns="columns"
        :rows="rows"
        row-key="id"
        :class="{ 'opacity-50': pending }"
      >
        <template #cell-client="{ row }">
          <div>
            <p class="font-medium text-neutral-900">{{ row.company }}</p>
            <p class="text-xs text-neutral-500">
              {{ row.clientName }} · Proposal #{{ row.proposalId }}
            </p>
          </div>
        </template>
        <template #cell-amount="{ row }">
          {{ row.currency }} {{ row.total }}
        </template>
        <template #cell-status="{ row }">
          <UBadge :color="statusColor(row.status)" variant="subtle">
            {{ row.status }}
          </UBadge>
        </template>
        <template #cell-action="{ row }">
          <UButton
            :to="`/quotations/${row.id}`"
            size="xs"
            color="neutral"
            variant="outline"
          >
            View
          </UButton>
        </template>
      </DataTable>
    </div>

    <div class="flex flex-col items-center justify-between gap-3 sm:flex-row">
      <p class="text-sm text-neutral-500">
        Showing {{ rangeStart }}-{{ rangeEnd }} of {{ total }} quotations
      </p>
      <UPagination v-model:page="page" :total="total" :items-per-page="limit" />
    </div>
  </main>
</template>

<script setup lang="ts">
interface ApiQuote {
  quote_id: number;
  proposal: {
    proposal_id: number;
    client_id: number;
    status: string;
    client: { name: string; company: string } | null;
  } | null;
  currency: string;
  total_amount: number;
  total: number;
  status: string;
  validity_days: number;
  created_at: string;
}

interface QuotesResponse {
  data: ApiQuote[];
  meta: { page: number; limit: number; total: number };
}

const status = ref("All statuses");
const page = ref(1);
const limit = ref(20);

const statuses = ["All statuses", "draft", "sent", "accepted", "expired"];

const columns = [
  { key: "client", label: "Proposal" },
  { key: "amount", label: "Amount" },
  { key: "status", label: "Status" },
  { key: "action", label: "" },
];

function onFilterChange() {
  page.value = 1;
}

function statusColor(s: string) {
  if (s === "accepted") return "success";
  if (s === "sent") return "warning";
  if (s === "expired") return "error";
  return "neutral";
}

const query = computed(() => ({
  page: page.value,
  limit: limit.value,
  status: status.value === "All statuses" ? undefined : status.value,
}));

const { data, pending, error } = useLazyFetch<QuotesResponse>("/api/quotes", {
  query,
  watch: [page, query],
});

const rows = computed(() =>
  (data.value?.data ?? []).map((quote) => ({
    id: quote.quote_id,
    proposalId: quote.proposal?.proposal_id ?? "—",
    company: quote.proposal?.client?.company ?? "—",
    clientName: quote.proposal?.client?.name ?? "",
    currency: quote.currency,
    total: Number(quote.total ?? quote.total_amount ?? 0).toLocaleString(),
    status: quote.status,
  })),
);

const total = computed(() => data.value?.meta?.total ?? 0);
const rangeStart = computed(() =>
  total.value === 0 ? 0 : (page.value - 1) * limit.value + 1,
);
const rangeEnd = computed(() => Math.min(page.value * limit.value, total.value));
</script>
