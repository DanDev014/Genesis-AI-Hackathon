<!-- pages/clients/[id].vue -->
<template>
  <div class="p-6 space-y-6">
    <!-- Loading -->
    <div v-if="pending" class="space-y-6">
      <!-- Header skeleton -->
      <div class="flex items-center gap-3">
        <USkeleton class="h-9 w-9 rounded-full bg-neutral-100" />
        <div class="space-y-2">
          <USkeleton class="h-6 w-48 bg-neutral-100" />
          <USkeleton class="h-3 w-32 bg-neutral-100" />
        </div>
        <USkeleton class="h-5 w-20 rounded-full bg-neutral-100 ml-2" />
      </div>

      <!-- Tabs skeleton -->
      <div class="flex items-center gap-6 border-b border-neutral-200 pb-3">
        <USkeleton class="h-4 w-16 bg-neutral-100" />
        <USkeleton class="h-4 w-20 bg-neutral-100" />
        <USkeleton class="h-4 w-20 bg-neutral-100" />
      </div>

      <!-- Card skeletons -->
      <div class="space-y-4">
        <UCard
          v-for="i in 3"
          :key="i"
          :ui="{ root: 'ring-0 bg-white shadow-md overflow-hidden' }"
        >
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <USkeleton class="h-4 w-4 rounded-full bg-neutral-100" />
              <USkeleton class="h-4 w-28 bg-neutral-100" />
            </div>
            <USkeleton class="h-3 w-24 bg-neutral-100" />
          </div>

          <USkeleton class="h-3 w-full bg-neutral-100 mb-2" />
          <USkeleton class="h-3 w-2/3 bg-neutral-100 mb-3" />

          <div class="flex items-center gap-3 pt-3 border-t border-neutral-200">
            <USkeleton class="h-6 w-20 rounded-md bg-neutral-100" />
            <USkeleton class="h-3 w-16 bg-neutral-100 ml-auto" />
          </div>
        </UCard>
      </div>
    </div>

    <!-- Error -->
    <UAlert
      v-else-if="error"
      color="error"
      variant="subtle"
      icon="i-lucide-alert-triangle"
      title="Couldn't load this client"
      :description="
        error.statusMessage || 'Something went wrong talking to the server.'
      "
    >
      <template #actions>
        <UButton size="xs" color="error" variant="soft" @click="refresh()">
          Retry
        </UButton>
        <UButton
          size="xs"
          color="neutral"
          variant="ghost"
          @click="navigateTo('/clients')"
        >
          Back to Clients
        </UButton>
      </template>
    </UAlert>

    <!-- Data -->
    <template v-else-if="client">
      <!-- Header -->
      <div class="flex items-center gap-3">
        <UButton
          icon="i-lucide-arrow-left"
          variant="ghost"
          color="primary"
          @click="navigateTo('/clients')"
        />
        <div>
          <h1 class="text-2xl font-bold">{{ client.company }}</h1>
          <p class="text-primary-500 text-sm">
            {{ client.name }} · {{ client.industry }}
          </p>
        </div>
        <UBadge
          :color="statusColor(client.status)"
          variant="subtle"
          class="ml-2"
        >
          {{ client.status }}
        </UBadge>
      </div>

      <!-- Tabs -->
      <UTabs :items="tabs" class="w-full mt-6">
        <template #calls>
          <div class="space-y-4 mt-4">
            <p
              v-if="client.calls.length === 0"
              class="text-neutral-400 text-sm"
            >
              No calls recorded yet.
            </p>

            <UCard
              v-for="call in client.calls"
              :key="call.call_id"
              :ui="{
                root: 'ring-0 bg-white shadow-md hover:shadow-lg transition-shadow duration-200 overflow-hidden',
              }"
            >
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-2">
                  <UIcon name="i-lucide-video" class="text-primary-500" />
                  <span class="font-medium text-neutral-900 capitalize">
                    {{ call.call_type }}
                  </span>
                </div>
                <span class="text-xs text-neutral-400">
                  {{ new Date(call.meeting_time).toLocaleString() }}
                </span>
              </div>

              <p
                v-if="call.transcript?.summary"
                class="text-sm text-neutral-600 mb-3"
              >
                {{ call.transcript.summary }}
              </p>
              <p v-else class="text-sm text-neutral-400 italic mb-3">
                Transcript not yet processed.
              </p>

              <div
                class="flex items-center gap-3 pt-3 border-t border-neutral-200"
              >
                <UButton
                  v-if="call.recording_url"
                  size="xs"
                  variant="soft"
                  color="primary"
                  icon="i-lucide-play"
                  :to="call.recording_url"
                  target="_blank"
                >
                  Recording
                </UButton>
                <span class="text-xs text-neutral-400 ml-auto">
                  {{ call.duration_minutes }} min
                </span>
              </div>
            </UCard>
          </div>
        </template>

        <template #intelligence>
          <div class="mt-4">
            <div
              v-if="!client.intelligence"
              class="flex flex-col items-center justify-center py-16 text-center"
            >
              <UIcon
                name="i-lucide-brain"
                class="w-10 h-10 text-neutral-300 mb-3"
              />
              <p class="text-neutral-500 font-medium">
                Intelligence not available yet
              </p>
              <p class="text-neutral-400 text-sm max-w-sm mt-1">
                Pain points, requirements, and objectives will appear here once
                the AI has processed this client's calls.
              </p>
            </div>

            <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <UCard
                v-for="section in intelligenceSections"
                :key="section.title"
                :ui="{
                  root: 'ring-0 bg-white shadow-md hover:shadow-lg transition-shadow duration-200 overflow-hidden',
                }"
              >
                <div class="-mx-4 -mt-4 mb-3 h-1.5 bg-orange-500" />
                <template #header>
                  <div class="flex items-center gap-2">
                    <UIcon :name="section.icon" class="text-orange-500" />
                    <span class="font-semibold text-neutral-900">{{
                      section.title
                    }}</span>
                  </div>
                </template>
                <ul class="space-y-2">
                  <li
                    v-for="(item, i) in section.items"
                    :key="i"
                    class="text-sm text-neutral-600 flex gap-2"
                  >
                    <span class="text-orange-500">•</span>
                    {{ item }}
                  </li>
                </ul>
              </UCard>
            </div>
          </div>
        </template>

        <template #proposals>
          <div class="space-y-3 mt-4">
            <p
              v-if="client.proposals.length === 0"
              class="text-neutral-400 text-sm"
            >
              No proposals yet.
            </p>

            <UCard
              v-for="p in client.proposals"
              :key="p.proposal_id"
              :ui="{
                root: 'ring-0 bg-white shadow-md hover:shadow-lg hover:-translate-y-1 transition-all duration-200 cursor-pointer overflow-hidden',
              }"
              @click="navigateTo(`/proposals/${p.proposal_id}`)"
            >
              <div class="-mx-4 -mt-4 mb-3 h-1.5 bg-orange-500" />
              <div class="flex items-center justify-between">
                <p class="font-medium text-neutral-900">
                  Proposal v{{ p.version }}
                </p>
                <UBadge :color="proposalStatusColor(p.status)" variant="subtle">
                  {{ p.status }}
                </UBadge>
              </div>
            </UCard>
          </div>
        </template>
      </UTabs>
    </template>
  </div>
</template>

<script setup lang="ts">
const route = useRoute();

const tabs = [
  { key: "calls", label: "Calls", icon: "i-lucide-phone-call", slot: "calls" },
  {
    key: "intelligence",
    label: "Intelligence",
    icon: "i-lucide-brain",
    slot: "intelligence",
  },
  {
    key: "proposals",
    label: "Proposals",
    icon: "i-lucide-file-text",
    slot: "proposals",
  },
];

const {
  data: client,
  pending,
  error,
  refresh,
} = useLazyFetch(() => `/api/clients/${route.params.id}`);

const intelligenceSections = computed(() => {
  const intel = client.value?.intelligence;
  if (!intel) return [];

  return [
    {
      title: "Pain Points",
      icon: "i-lucide-alert-triangle",
      items: intel.pain_points ?? [],
    },
    {
      title: "Requirements",
      icon: "i-lucide-list-checks",
      items: intel.requirements ?? [],
    },
    {
      title: "Objectives",
      icon: "i-lucide-target",
      items: intel.objectives ?? [],
    },
  ];
});

function statusColor(status: string) {
  const map: Record<string, string> = {
    lead: "neutral",
    contacted: "info",
    "proposal sent": "warning",
    "active client": "success",
    won: "success",
    lost: "error",
  };
  return map[status?.toLowerCase()] ?? "neutral";
}

function proposalStatusColor(status: string) {
  const map: Record<string, string> = {
    draft: "neutral",
    pending_review: "warning",
    approved: "info",
    sent: "primary",
    accepted: "success",
    rejected: "error",
  };
  return map[status?.toLowerCase()] ?? "neutral";
}
</script>
