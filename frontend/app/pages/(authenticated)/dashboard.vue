<template>
  <main class="space-y-8 p-6 lg:p-8">
    <section class="flex flex-col justify-between gap-5 md:flex-row md:items-end">
      <div>
        <h1 class="mt-1 text-3xl font-semibold tracking-tight text-black">
          Good morning, Genesis team.
        </h1>
      </div>
      <UButton to="/tafsiri" icon="i-lucide-sparkles" class="text-white">
        Process a meeting
      </UButton>
    </section>

    <p v-if="error" class="text-sm text-red-600">
      Couldn't load dashboard data. Please try again.
    </p>

    <!-- Metrics -->
    <section v-if="pending" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
      <USkeleton v-for="i in 5" :key="i" class="h-28 w-full rounded-2xl bg-neutral-200" />
    </section>
    <section v-else class="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
      <MetricCard
        label="Active clients"
        :value="String(metrics?.total_clients ?? 0)"
        :detail="`${metrics?.clients_this_month ?? 0} added this month`"
        icon="i-lucide-building-2"
      />
      <MetricCard
        label="Meetings processed"
        :value="String(metrics?.meetings_processed ?? 0)"
        detail="Captured via Tafsiri"
        icon="i-lucide-audio-lines"
      />
      <MetricCard
        label="Proposals in review"
        :value="String(metrics?.proposals_in_review ?? 0)"
        :detail="`KES ${formatNumber(metrics?.pipeline_value ?? 0)} pipeline value`"
        icon="i-lucide-file-check-2"
      />
      <MetricCard
        label="Win rate"
        :value="`${metrics?.win_rate ?? 0}%`"
        detail="Accepted vs. decided quotations"
        icon="i-lucide-trending-up"
      />
      <MetricCard
        label="Time to proposal"
        :value="timeToProposalValue"
        detail="Meeting to delivered draft, avg"
        icon="i-lucide-timer"
      />
    </section>

    <section class="grid gap-6 xl:grid-cols-5">
      <UCard class="xl:col-span-3" :ui="{ root: 'ring-0 border border-neutral-200 !bg-white shadow-sm' }">
        <template #header>
          <div class="flex items-center justify-between">
            <div>
              <h2 class="font-semibold text-neutral-950">Pipeline</h2>
              <p class="mt-1 text-sm text-neutral-500">Proposals by status</p>
            </div>
          </div>
        </template>
        <div v-if="pending" class="flex h-72 items-end gap-4 px-2 pt-4">
          <USkeleton v-for="i in 4" :key="i" class="h-full w-full bg-neutral-100" />
        </div>
        <div v-else-if="pipeline.length" class="flex h-72 items-end gap-4 px-2 pt-4">
          <div
            v-for="stage in pipeline"
            :key="stage.label"
            class="flex flex-1 flex-col items-center gap-3"
          >
            <div class="flex h-52 w-full items-end rounded-t-xl bg-neutral-100 px-2">
              <div
                class="w-full rounded-t-lg bg-[#e0b818] transition-all"
                :style="{ height: `${pipelinePercent(stage.count)}%` }"
              />
            </div>
            <div class="text-center">
              <p class="text-xs font-medium text-neutral-700">{{ stage.label }}</p>
              <p class="mt-1 text-xs text-neutral-500">{{ stage.count }}</p>
            </div>
          </div>
        </div>
        <p v-else class="py-12 text-center text-sm text-neutral-500">No proposals yet.</p>
      </UCard>

      <UCard class="xl:col-span-2" :ui="{ root: 'ring-0 border border-neutral-200 bg-black text-white shadow-sm' }">
        <template #header>
          <div class="flex items-center gap-2">
            <span class="flex size-8 items-center justify-center rounded-lg bg-[#e0b818] text-black">
              <UIcon name="i-lucide-sparkles" />
            </span>
            <div>
              <h2 class="font-semibold">Tafsiri</h2>
              <p class="text-xs text-neutral-400">Meeting intelligence</p>
            </div>
          </div>
        </template>
        <div class="space-y-5">
          <p class="text-sm leading-6 text-neutral-300">
            Drop in a Fathom transcript to produce a discovery summary or a proposal-ready
            strategy pack.
          </p>
          <UButton to="/tafsiri" block class="text-white">
            Open AI workspace
          </UButton>
        </div>
      </UCard>
    </section>

    <section class="grid gap-6 xl:grid-cols-5">
      <div class="xl:col-span-5">
        <div class="mb-4 flex items-center justify-between">
          <div>
            <h2 class="font-semibold text-neutral-950">Recent activity</h2>
            <p class="text-sm text-neutral-500">Latest movement across the pipeline</p>
          </div>
          <UButton to="/clients" variant="link" color="neutral">View clients</UButton>
        </div>
        <TableSkeleton v-if="pending" :columns="4" :rows="5" />
        <DataTable v-else :columns="activityColumns" :rows="activityRows" row-key="id">
          <template #cell-client="{ row }">
            <div>
              <p class="font-medium text-neutral-900">{{ row.client }}</p>
              <p class="text-xs text-neutral-500">{{ row.company }}</p>
            </div>
          </template>
          <template #cell-status="{ row }">
            <UBadge color="warning" variant="subtle">{{ row.status }}</UBadge>
          </template>
        </DataTable>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
interface DashboardResponse {
  success: boolean;
  data: {
    metrics: {
      total_clients: number;
      clients_this_month: number;
      meetings_processed: number;
      proposals_in_review: number;
      pipeline_value: number;
      win_rate: number;
      avg_time_to_proposal_hours: number | null;
    };
    pipeline: { label: string; count: number }[];
    recent_activity: {
      id: string;
      client: string;
      company: string;
      activity: string;
      status: string;
      created_at: string | null;
    }[];
  };
}

const { data: response, pending, error } = await useLazyFetch<DashboardResponse>("/api/dashboard");

const metrics = computed(() => response.value?.data?.metrics ?? null);
const pipeline = computed(() => response.value?.data?.pipeline ?? []);

const activityColumns = [
  { key: "client", label: "Client" },
  { key: "activity", label: "Activity" },
  { key: "status", label: "Status" },
  { key: "time", label: "Updated" },
];

function timeAgo(iso: string | null) {
  if (!iso) return "—";
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  return `${Math.floor(hours / 24)} d ago`;
}

const activityRows = computed(() =>
  (response.value?.data?.recent_activity ?? []).map((item) => ({
    id: item.id,
    client: item.client,
    company: item.company,
    activity: item.activity,
    status: item.status,
    time: timeAgo(item.created_at),
  })),
);

function pipelinePercent(count: number) {
  const max = Math.max(...pipeline.value.map((p) => p.count), 1);
  return Math.round((count / max) * 100);
}

function formatNumber(n: number) {
  return Number(n ?? 0).toLocaleString();
}

const timeToProposalValue = computed(() => {
  const hours = metrics.value?.avg_time_to_proposal_hours;
  if (hours == null) return "—";
  if (hours < 24) return `${hours}h`;
  return `${(hours / 24).toFixed(1)}d`;
});
</script>
