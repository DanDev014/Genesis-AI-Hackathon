<template>
  <main class="flex flex-col gap-4 p-6">
    <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <h1 class="mt-1 text-xl font-semibold tracking-tight text-black">
          Proposals
        </h1>
      </div>
      <UButton to="/tafsiri" icon="i-lucide-sparkles" class="text-white">
        Generate proposal
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
      Couldn't load proposals. Please try again.
    </p>

    <!-- Initial load: no data yet -->
    <TableSkeleton v-if="pending && !data" :columns="5" :rows="8" />

    <!-- Loaded (or refetching) -->
    <div v-else class="relative">
      <div
        v-if="pending"
        class="absolute inset-0 z-10 flex items-center justify-center gap-2 rounded-lg bg-white/70 text-sm text-neutral-500"
      >
        <UIcon name="i-lucide-loader-2" class="size-4 animate-spin" />
        Loading proposals...
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
            <p class="text-xs text-neutral-500">{{ row.clientName }}</p>
          </div>
        </template>
        <template #cell-scope="{ row }">
          <p class="max-w-xs truncate text-neutral-700">{{ row.scope }}</p>
        </template>
        <template #cell-status="{ row }">
          <UBadge :color="statusColor(row.status)" variant="subtle">
            {{ row.status }}
          </UBadge>
        </template>
        <template #cell-version="{ row }">v{{ row.version }}</template>
        <template #cell-action="{ row }">
          <UButton
            :to="`/proposals/${row.id}`"
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
        Showing {{ rangeStart }}-{{ rangeEnd }} of {{ total }} proposals
      </p>
      <UPagination v-model:page="page" :total="total" :items-per-page="limit" />
    </div>
  </main>
</template>

<script setup lang="ts">
interface ApiProposal {
  proposal_id: number;
  client: { client_id: number; name: string; company: string } | null;
  scope_of_work: string;
  status: string;
  version: number;
  created_at: string;
}

interface ProposalsResponse {
  data: ApiProposal[];
  meta: { page: number; limit: number; total: number };
}

const status = ref("All statuses");
const page = ref(1);
const limit = ref(20);

const statuses = ["All statuses", "draft", "sent", "revised", "accepted", "rejected"];

const columns = [
  { key: "client", label: "Client" },
  { key: "scope", label: "Scope" },
  { key: "version", label: "Version" },
  { key: "status", label: "Status" },
  { key: "action", label: "" },
];

function onFilterChange() {
  page.value = 1;
}

function statusColor(s: string) {
  if (s === "accepted") return "success";
  if (s === "sent" || s === "revised") return "warning";
  if (s === "rejected") return "error";
  return "neutral";
}

const query = computed(() => ({
  page: page.value,
  limit: limit.value,
  status: status.value === "All statuses" ? undefined : status.value,
}));

const { data, pending, error } = useLazyFetch<ProposalsResponse>("/api/proposals", {
  query,
  watch: [page, query],
});

const rows = computed(() =>
  (data.value?.data ?? []).map((proposal) => ({
    id: proposal.proposal_id,
    company: proposal.client?.company ?? "—",
    clientName: proposal.client?.name ?? "",
    scope: proposal.scope_of_work || "Not yet established.",
    status: proposal.status,
    version: proposal.version,
  })),
);

const total = computed(() => data.value?.meta?.total ?? 0);
const rangeStart = computed(() =>
  total.value === 0 ? 0 : (page.value - 1) * limit.value + 1,
);
const rangeEnd = computed(() => Math.min(page.value * limit.value, total.value));
</script>
