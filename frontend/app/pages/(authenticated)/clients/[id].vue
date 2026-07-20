<!-- pages/clients/[id].vue -->
<template>
  <div class="p-6 space-y-6">
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
      <UBadge :color="statusColor(client.status)" variant="subtle" class="ml-2">
        {{ client.status }}
      </UBadge>
    </div>

    <!-- Tabs -->
    <UTabs :items="tabs" class="w-full">
      <template #calls>
        <div class="space-y-4 mt-4">
          <UCard
            v-for="call in calls"
            :key="call.call_id"
            :ui="{
              root: 'ring-0 bg-white shadow-md hover:shadow-lg transition-shadow duration-200 overflow-hidden',
            }"
          >
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide-video" class="text-primary-500" />
                <span class="font-medium text-neutral-900">{{
                  call.call_type
                }}</span>
              </div>
              <span class="text-xs text-neutral-400">{{
                call.meeting_time
              }}</span>
            </div>

            <p class="text-sm text-neutral-600 mb-3">
              {{ call.transcript.summary }}
            </p>

            <div
              class="flex items-center gap-3 pt-3 border-t border-neutral-200"
            >
              <UButton
                size="xs"
                variant="soft"
                color="primary"
                icon="i-lucide-play"
                :to="call.recording_url"
                target="_blank"
              >
                Recording
              </UButton>
              <UButton
                size="xs"
                variant="ghost"
                color="neutral"
                icon="i-lucide-file-text"
                @click="openTranscript(call)"
              >
                Full Transcript
              </UButton>
              <span class="text-xs text-neutral-400 ml-auto">
                {{ call.duration_minutes }} min · {{ call.platform }}
              </span>
            </div>
          </UCard>
        </div>
      </template>

      <template #intelligence>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
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
      </template>

      <template #proposals>
        <div class="space-y-3 mt-4">
          <UCard
            v-for="p in proposals"
            :key="p.proposal_id"
            :ui="{
              root: 'ring-0 bg-white shadow-md hover:shadow-lg hover:-translate-y-1 transition-all duration-200 cursor-pointer overflow-hidden',
            }"
            @click="navigateTo(`/proposals/${p.proposal_id}`)"
          >
            <div class="-mx-4 -mt-4 mb-3 h-1.5 bg-orange-500" />

            <div class="flex items-center justify-between">
              <div>
                <p class="font-medium text-neutral-900">
                  Proposal v{{ p.version }}
                </p>
                <p class="text-xs text-neutral-400">
                  Generated {{ p.created_at }}
                </p>
              </div>
              <div class="flex items-center gap-3">
                <span class="text-orange-500 font-semibold">
                  KES {{ p.total_amount.toLocaleString() }}
                </span>
                <UBadge :color="proposalStatusColor(p.status)" variant="subtle">
                  {{ p.status }}
                </UBadge>
              </div>
            </div>
          </UCard>
        </div>
      </template>
    </UTabs>

    <!-- Transcript Modal -->
    <UModal v-model="isTranscriptOpen">
      <UCard :ui="{ root: 'ring-0 bg-white shadow-xl' }">
        <template #header>
          <h3 class="font-semibold text-neutral-900">Full Transcript</h3>
        </template>
        <div class="space-y-3 max-h-96 overflow-y-auto">
          <div v-for="(seg, i) in selectedTranscript" :key="i" class="text-sm">
            <span class="text-orange-500 font-medium">{{ seg.speaker }}:</span>
            <span class="text-neutral-600"> {{ seg.text }}</span>
          </div>
        </div>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
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

// Dummy seeded data — replace with GET /api/clients/:id
const client = ref({
  client_id: 1,
  name: "John Kariuki",
  company: "Acme Corp",
  industry: "Retail",
  status: "active",
});

const calls = ref([
  {
    call_id: 55,
    call_type: "Discovery Call",
    meeting_time: "Jul 18, 2:00 PM",
    duration_minutes: 45,
    platform: "Zoom",
    recording_url: "#",
    transcript: {
      summary:
        "Client is looking to modernize their onboarding process and integrate a CRM. Budget flexible, timeline is Q4.",
      segments: [
        {
          speaker: "Client",
          text: "Our biggest issue is onboarding takes too long.",
        },
        {
          speaker: "Account Manager",
          text: "Got it — can you walk me through the current process?",
        },
      ],
    },
  },
]);

const intelligenceSections = ref([
  {
    title: "Pain Points",
    icon: "i-lucide-alert-triangle",
    items: ["Slow onboarding process", "Manual reporting takes 3+ days"],
  },
  {
    title: "Requirements",
    icon: "i-lucide-list-checks",
    items: ["CRM integration", "Mobile access for field team"],
  },
  {
    title: "Objectives",
    icon: "i-lucide-target",
    items: ["20% cost reduction by Q4", "Faster client onboarding"],
  },
]);

const proposals = ref([
  {
    proposal_id: 21,
    version: 2,
    status: "sent",
    total_amount: 250000,
    created_at: "Jul 19, 2026",
  },
]);

const isTranscriptOpen = ref(false);
const selectedTranscript = ref<any[]>([]);

function openTranscript(call: any) {
  selectedTranscript.value = call.transcript.segments;
  isTranscriptOpen.value = true;
}

function statusColor(status: string) {
  const map: Record<string, string> = {
    active: "success",
    lead: "warning",
    dormant: "neutral",
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
