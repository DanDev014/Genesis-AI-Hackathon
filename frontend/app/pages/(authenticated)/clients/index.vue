<template>
  <div class="p-6 space-y-6 text-white">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl text-black font-bold">Clients</h1>
        <p class="text-neutral-400 text-sm">
          {{ filteredClients.length }} clients tracked
        </p>
      </div>
      <div class="flex items-center gap-3">
        <UInput
          v-model="search"
          icon="i-lucide-search"
          placeholder="Search clients..."
          class="w-64"
          :ui="{
            base: 'bg-white text-neutral-900 ring-1 ring-neutral-300 focus:ring-2 focus:ring-yellow-500 focus-visible:ring-2 focus-visible:ring-orange-500',
          }"
        />

        <USelect
          v-model="statusFilter"
          :items="statusOptions"
          placeholder="Filter"
          class="w-40"
          :ui="{
            base: 'bg-white text-neutral-900 ring-1 ring-neutral-300 focus:ring-2 focus:ring-yellow-500 focus-visible:ring-2 focus-visible:ring-orange-500',
          }"
        />
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <UCard
        v-for="client in filteredClients"
        :key="client.client_id"
        :ui="{
          root: 'ring-0 bg-white shadow-md hover:shadow-xl hover:-translate-y-1 transition-all duration-200 cursor-pointer overflow-hidden',
        }"
        @click="navigateTo(`/clients/${client.client_id}`)"
      >
        <div class="flex items-start justify-between mb-3">
          <div>
            <h3 class="font-semibold text-neutral-900">{{ client.company }}</h3>
            <p class="text-sm text-neutral-500">{{ client.name }}</p>
          </div>
          <UBadge
            :color="statusColor(client.status)"
            variant="subtle"
            size="sm"
          >
            {{ client.status }}
          </UBadge>
        </div>

        <div class="flex items-center gap-2 text-sm text-neutral-500 mb-3">
          <UIcon name="i-lucide-briefcase" class="w-4 h-4 text-primary-500" />
          {{ client.industry }}
        </div>

        <div
          class="flex items-center justify-between pt-3 border-t border-neutral-200 text-xs text-neutral-500"
        >
          <span class="flex items-center gap-1">
            <UIcon
              name="i-lucide-phone-call"
              class="w-3.5 h-3.5 text-primary-500 text-bold"
            />
            {{ client.call_count }} calls
          </span>
          <span class="flex items-center gap-1">
            <UIcon
              name="i-lucide-file-text"
              class="w-3.5 h-3.5 text-primary-500 text-bold"
            />
            {{ client.proposal_count }} proposals
          </span>
        </div>
      </UCard>
    </div>
  </div>
</template>

<script setup lang="ts">
const search = ref("");
const statusFilter = ref<string | null>(null);

const statusOptions = [
  { label: "All Statuses", value: null },
  { label: "Active", value: "active" },
  { label: "Lead", value: "lead" },
  { label: "Dormant", value: "dormant" },
  { label: "Lost", value: "lost" },
];

const clients = ref([
  {
    client_id: 1,
    name: "John Kariuki",
    company: "Acme Corp",
    industry: "Retail",
    status: "active",
    call_count: 3,
    proposal_count: 2,
  },
  {
    client_id: 2,
    name: "Mary Wanjiru",
    company: "Zeta Ltd",
    industry: "Finance",
    status: "lead",
    call_count: 1,
    proposal_count: 0,
  },
  {
    client_id: 3,
    name: "Peter Otieno",
    company: "Nova Traders",
    industry: "Logistics",
    status: "active",
    call_count: 5,
    proposal_count: 3,
  },
]);

const filteredClients = computed(() =>
  clients.value.filter((c) => {
    const matchesSearch =
      c.company.toLowerCase().includes(search.value.toLowerCase()) ||
      c.name.toLowerCase().includes(search.value.toLowerCase());
    const matchesStatus =
      !statusFilter.value || c.status === statusFilter.value;
    return matchesSearch && matchesStatus;
  }),
);

function statusColor(status: string) {
  const map: Record<string, string> = {
    active: "success",
    lead: "warning",
    dormant: "neutral",
    lost: "error",
  };
  return map[status?.toLowerCase()] ?? "neutral";
}
</script>
