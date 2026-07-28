<template>
  <main class="space-y-6 p-6 lg:p-8">
    <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <h1 class="mt-1 text-3xl font-semibold tracking-tight text-black">
          Summaries
        </h1>
      </div>
      <UButton to="/tafsiri" icon="i-lucide-upload" class="text-white">
        Process transcript
      </UButton>
    </div>

    <p v-if="error" class="text-sm text-red-600">
      Couldn't load summaries. Please try again.
    </p>

    <!-- Initial load: no data yet -->
    <TableSkeleton v-if="pending && !data" :columns="5" :rows="8" />

    <div v-else class="relative">
      <div
        v-if="pending"
        class="absolute inset-0 z-10 flex items-center justify-center gap-2 rounded-lg bg-white/70 text-sm text-neutral-500"
      >
        <UIcon name="i-lucide-loader-2" class="size-4 animate-spin" />
        Loading summaries...
      </div>
      <DataTable
        :columns="columns"
        :rows="rows"
        row-key="id"
        :class="{ 'opacity-50': pending }"
      >
        <template #cell-type="{ row }">
          <UBadge :color="row.type === 'internal' ? 'warning' : 'neutral'" variant="subtle">
            {{ row.type }}
          </UBadge>
        </template>
        <template #cell-action="{ row }">
          <UButton
            :to="`/summaries/${row.id}`"
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
        Showing {{ rangeStart }}-{{ rangeEnd }} of {{ total }} summaries
      </p>
      <UPagination v-model:page="page" :total="total" :items-per-page="limit" />
    </div>
  </main>
</template>

<script setup lang="ts">
interface ApiSummary {
  summary_id: number;
  client_id: number;
  first_meeting_deliverables: {
    title?: string;
    meeting_type?: string;
    key_points?: { client?: { company?: string } };
  } | null;
  created_at: string;
}

interface SummariesResponse {
  data: ApiSummary[];
  meta: { page: number; limit: number; total: number };
}

const page = ref(1);
const limit = ref(20);

const columns = [
  { key: "title", label: "Meeting summary" },
  { key: "client", label: "Client" },
  { key: "type", label: "Meeting type" },
  { key: "date", label: "Created" },
  { key: "action", label: "" },
];

const query = computed(() => ({ page: page.value, limit: limit.value }));

const { data, pending, error } = useLazyFetch<SummariesResponse>("/api/summaries", {
  query,
  watch: [page],
});

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

const rows = computed(() =>
  (data.value?.data ?? []).map((summary) => {
    const meeting = summary.first_meeting_deliverables;
    return {
      id: summary.summary_id,
      title: meeting?.title || "Untitled meeting",
      client: meeting?.key_points?.client?.company || "—",
      type: meeting?.meeting_type || "unknown",
      date: formatDate(summary.created_at),
    };
  }),
);

const total = computed(() => data.value?.meta?.total ?? 0);
const rangeStart = computed(() =>
  total.value === 0 ? 0 : (page.value - 1) * limit.value + 1,
);
const rangeEnd = computed(() => Math.min(page.value * limit.value, total.value));
</script>
