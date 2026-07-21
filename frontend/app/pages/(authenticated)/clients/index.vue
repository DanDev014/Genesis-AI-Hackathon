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
            base: 'bg-white text-neutral-900 ring-1 ring-neutral-300 focus:ring-2 focus:ring-orange-500 focus-visible:ring-2 focus-visible:ring-orange-500',
          }"
        />

        <USelect
          v-model="statusFilter"
          :items="statusOptions"
          placeholder="Filter"
          class="w-40"
          :ui="{
            base: 'bg-white text-neutral-900 ring-1 ring-neutral-300 focus:ring-2 focus:ring-orange-500 focus-visible:ring-2 focus-visible:ring-orange-500',
          }"
        />
      </div>
    </div>

    <!-- Loading -->
    <div
      v-if="pending"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
    >
      <USkeleton v-for="i in 6" :key="i" class="h-32 w-full rounded-lg" />
    </div>

    <!-- Error — surfaces the real DB/backend message from apiRequest -->
    <UAlert
      v-else-if="error"
      color="error"
      variant="subtle"
      icon="i-lucide-alert-triangle"
      title="Couldn't load clients"
      :description="
        error.statusMessage || 'Something went wrong talking to the server.'
      "
    >
      <template #actions>
        <UButton size="xs" color="error" variant="soft" @click="refresh()">
          Retry
        </UButton>
      </template>
    </UAlert>

    <!-- Empty -->
    <div
      v-else-if="filteredClients.length === 0"
      class="text-neutral-400 text-center py-12"
    >
      No clients match your filters.
    </div>

    <!-- Data -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
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
            <UIcon name="i-lucide-user" class="w-3.5 h-3.5 text-primary-500" />
            {{ client.assigned_account_manager?.full_name ?? "Unassigned" }}
          </span>
          <span class="flex items-center gap-1">
            <UIcon
              name="i-lucide-phone-call"
              class="w-3.5 h-3.5 text-primary-500"
            />
            {{
              client.last_call_at
                ? new Date(client.last_call_at).toLocaleDateString()
                : "No calls yet"
            }}
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
  { label: "Lead", value: "lead" },
  { label: "Contacted", value: "contacted" },
  { label: "Proposal Sent", value: "proposal sent" },
  { label: "Active Client", value: "active client" },
  { label: "Won", value: "won" },
  { label: "Lost", value: "lost" },
];

// Calls the BFF route (server/api/clients/index.get.ts), which proxies to Flask
const { data, pending, error, refresh } = await useFetch("/api/clients");

const clients = computed(() => data.value?.data ?? []);

const filteredClients = computed(() =>
  clients.value.filter((c: any) => {
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
    lead: "neutral",
    contacted: "info",
    "proposal sent": "warning",
    "active client": "success",
    won: "success",
    lost: "error",
  };
  return map[status?.toLowerCase()] ?? "neutral";
}
</script>
