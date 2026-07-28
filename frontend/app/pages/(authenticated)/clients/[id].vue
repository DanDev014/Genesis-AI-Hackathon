<template>
  <main class="space-y-6 p-6 lg:p-8">
    <UButton to="/clients" icon="i-lucide-arrow-left" color="neutral" variant="link" class="-ml-2">
      Back to clients
    </UButton>

    <div v-if="pending" class="space-y-6">
      <USkeleton class="h-32 w-full rounded-2xl bg-neutral-200" />
      <USkeleton class="h-64 w-full rounded-2xl bg-neutral-200" />
    </div>

    <p v-else-if="error" class="text-sm text-red-600">
      Couldn't load this client. Please try again.
    </p>

    <template v-else-if="client">
      <section
        class="flex flex-col justify-between gap-4 rounded-2xl bg-black p-6 text-white md:flex-row md:items-end"
      >
        <div>
          <div class="flex items-center gap-3">
            <span
              class="flex size-11 items-center justify-center rounded-xl bg-[#e0b818] text-lg font-bold text-black"
            >
              {{ initials }}
            </span>
            <div>
              <p class="text-sm text-neutral-400">Client account</p>
              <h1 class="text-2xl font-semibold">{{ client.company }}</h1>
            </div>
          </div>
          <p class="mt-5 text-sm text-neutral-300">
            {{ client.name }} · {{ client.email }}
            <span v-if="client.phone"> · {{ client.phone }}</span>
          </p>
        </div>
        <div class="flex gap-3">
          <UBadge color="warning" variant="subtle">{{ client.status || "Unknown" }}</UBadge>
          <UButton to="/tafsiri" class="text-white">
            Process meeting
          </UButton>
        </div>
      </section>

      <div class="flex gap-2 border-b border-neutral-200">
        <button
          v-for="item in tabs"
          :key="item"
          class="border-b-2 px-4 py-3 text-sm font-medium transition"
          :class="
            tab === item
              ? 'border-[#e0b818] text-neutral-950'
              : 'border-transparent text-neutral-500 hover:text-neutral-900'
          "
          @click="tab = item"
        >
          {{ item }}
        </button>
      </div>

      <section v-if="tab === 'Overview'" class="grid gap-6 xl:grid-cols-5">
        <div class="space-y-6 xl:col-span-3">
          <UCard :ui="{ root: 'ring-0 border border-neutral-200 !bg-white shadow-sm' }">
            <template #header>
              <h2 class="font-semibold text-neutral-950">Account overview</h2>
            </template>
            <div class="grid gap-5 sm:grid-cols-3">
              <div v-for="item in overview" :key="item.label">
                <p class="text-xs uppercase tracking-wider text-neutral-500">{{ item.label }}</p>
                <p class="mt-2 text-sm font-medium text-neutral-900">{{ item.value }}</p>
              </div>
            </div>
          </UCard>
        </div>

        <UCard class="xl:col-span-2" :ui="{ root: 'ring-0 border border-neutral-200 !bg-white shadow-sm' }">
          <template #header>
            <h2 class="font-semibold text-neutral-950">Activity</h2>
          </template>
          <div class="space-y-3 text-sm text-neutral-700">
            <p>{{ summaries.length }} meeting summar{{ summaries.length === 1 ? "y" : "ies" }}</p>
            <p>{{ proposals.length }} proposal{{ proposals.length === 1 ? "" : "s" }}</p>
          </div>
        </UCard>
      </section>

      <section v-else-if="tab === 'Summaries'" class="space-y-4">
        <div v-if="summariesPending" class="space-y-2">
          <USkeleton class="h-24 w-full rounded-2xl bg-neutral-200" />
        </div>
        <div
          v-for="summary in summaries"
          v-else
          :key="summary.summary_id"
          class="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm"
        >
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="font-semibold text-neutral-950">
                {{ summary.first_meeting_deliverables?.title || "Untitled meeting" }}
              </p>
              <p class="mt-2 text-sm leading-6 text-neutral-600">
                {{ summary.first_meeting_deliverables?.key_points?.project?.objective || "" }}
              </p>
            </div>
            <UBadge color="warning" variant="subtle">
              {{ summary.first_meeting_deliverables?.meeting_type || "unknown" }}
            </UBadge>
          </div>
          <UButton
            :to="`/summaries/${summary.summary_id}`"
            size="xs"
            color="neutral"
            variant="outline"
            class="mt-3"
          >
            View
          </UButton>
        </div>
        <p v-if="!summariesPending && !summaries.length" class="text-sm text-neutral-500">
          No summaries yet.
        </p>
      </section>

      <section v-else class="space-y-4">
        <div v-if="proposalsPending" class="space-y-2">
          <USkeleton class="h-20 w-full rounded-2xl bg-neutral-200" />
        </div>
        <div
          v-for="proposal in proposals"
          v-else
          :key="proposal.proposal_id"
          class="flex flex-col justify-between gap-4 rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm sm:flex-row sm:items-center"
        >
          <div>
            <p class="font-semibold text-neutral-950">
              {{ proposal.scope_of_work || "Untitled proposal" }}
            </p>
            <p class="mt-1 text-sm text-neutral-500">Version {{ proposal.version }}</p>
          </div>
          <div class="flex items-center gap-3">
            <UBadge color="warning" variant="subtle">{{ proposal.status }}</UBadge>
            <UButton
              :to="`/proposals/${proposal.proposal_id}`"
              color="neutral"
              variant="outline"
              size="sm"
            >
              View
            </UButton>
          </div>
        </div>
        <p v-if="!proposalsPending && !proposals.length" class="text-sm text-neutral-500">
          No proposals yet.
        </p>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
const route = useRoute();
const clientId = route.params.id as string;

const tab = ref("Overview");
const tabs = ["Overview", "Summaries", "Proposals"];

const {
  data: clientResponse,
  pending,
  error,
} = await useLazyFetch<{ success: boolean; data: any }>(`/api/clients/${clientId}`);

const client = computed(() => clientResponse.value?.data ?? null);

const { data: summariesResponse, pending: summariesPending } = await useLazyFetch<{
  data: any[];
}>("/api/summaries", { query: { client_id: clientId } });
const summaries = computed(() => summariesResponse.value?.data ?? []);

const { data: proposalsResponse, pending: proposalsPending } = await useLazyFetch<{
  data: any[];
}>("/api/proposals", { query: { client_id: clientId } });
const proposals = computed(() => proposalsResponse.value?.data ?? []);

const initials = computed(() => {
  const name = client.value?.company || "";
  return name
    .split(" ")
    .map((w: string) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
});

const overview = computed(() => [
  { label: "Account owner", value: client.value?.assigned_account_manager?.full_name ?? "Unassigned" },
  { label: "Industry", value: client.value?.industry ?? "—" },
  { label: "Source", value: client.value?.source ?? "—" },
  { label: "Status", value: client.value?.status ?? "—" },
  {
    label: "Client since",
    value: client.value?.created_at
      ? new Date(client.value.created_at).toLocaleDateString("en-US", {
          month: "short",
          year: "numeric",
        })
      : "—",
  },
  { label: "Last call", value: client.value?.last_call_at ? new Date(client.value.last_call_at).toLocaleDateString() : "No calls yet" },
]);
</script>
