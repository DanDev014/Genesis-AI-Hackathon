<template>
  <main class="flex flex-col gap-4 p-6">
    <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <h1 class="mt-1 text-xl font-semibold tracking-tight text-primary">
          Clients
        </h1>
      </div>
      <UButton
        icon="i-lucide-user-plus"
        class="text-white font-semibold bg-primary hover:bg-yellow-400"
        >Add client</UButton
      >
    </div>
    <div class="flex flex-row gap-3 w-full sm:flex-row">
      <UInput
        v-model="search"
        icon="i-lucide-search"
        placeholder="Search clients or company..."
        class="w-full sm:max-w-sm"
        :ui="{
          base: 'bg-white text-neutral-900 ring-neutral-200 focus:ring-2 focus:ring-[#e0b818]',
        }"
        @update:model-value="onFilterChange"
      /><USelect
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
      Couldn't load clients. Please try again.
    </p>

    <DataTable
      :columns="columns"
      :rows="rows"
      :loading="pending"
      row-key="client_id"
      ><template #cell-client="{ row }"
        ><div>
          <p class="font-medium text-neutral-900">{{ row.name }}</p>
          <p class="text-xs text-neutral-500">{{ row.industry }}</p>
        </div></template
      ><template #cell-status="{ row }"
        ><UBadge
          :color="
            row.status === 'Active'
              ? 'success'
              : row.status === 'Proposal sent'
                ? 'warning'
                : 'neutral'
          "
          variant="subtle"
          >{{ row.status || "Unknown" }}</UBadge
        ></template
      ><template #cell-owner="{ row }">{{ row.owner }}</template
      ><template #cell-lastMeeting="{ row }">{{ row.lastMeeting }}</template
      ><template #cell-action="{ row }"
        ><UButton
          :to="`/clients/${row.client_id}`"
          color="neutral"
          variant="outline"
          size="xs"
          >View client</UButton
        ></template
      ></DataTable
    >

    <div class="flex flex-col items-center justify-between gap-3 sm:flex-row">
      <p class="text-sm text-neutral-500">
        Showing {{ rangeStart }}-{{ rangeEnd }} of {{ total }} clients
      </p>
      <UPagination v-model:page="page" :total="total" :items-per-page="limit" />
    </div>
  </main>
</template>

<script setup lang="ts">
interface AccountManager {
  staff_id: number;
  full_name: string;
}

interface ApiClient {
  client_id: number;
  name: string;
  company: string;
  industry: string;
  status: string | null;
  assigned_account_manager: AccountManager | null;
  last_call_at: string | null;
  created_at: string;
}

interface ClientsResponse {
  data: ApiClient[];
  meta: { page: number; limit: number; total: number };
}

const search = ref("");
const debouncedSearch = ref("");
const status = ref("All statuses");
const page = ref(1);
const limit = ref(20);

const statuses = [
  "All statuses",
  "Active",
  "Discovery",
  "Proposal sent",
  "Won",
];

const columns = [
  { key: "client", label: "Client" },
  { key: "company", label: "Company" },
  { key: "status", label: "Status" },
  { key: "owner", label: "Account owner" },
  { key: "lastMeeting", label: "Last meeting" },
  { key: "action", label: "" },
];

let debounceTimer: ReturnType<typeof setTimeout>;
function onFilterChange() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    debouncedSearch.value = search.value;
    page.value = 1;
  }, 300);
}

const query = computed(() => ({
  page: page.value,
  limit: limit.value,
  search: debouncedSearch.value || undefined,
  status: status.value === "All statuses" ? undefined : status.value,
}));

const { data, pending, error } = useLazyFetch<ClientsResponse>("/api/clients", {
  query,
  watch: [page, query],
});

function formatDate(iso: string | null) {
  if (!iso) return "No calls yet";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

const rows = computed(() =>
  (data.value?.data ?? []).map((client) => ({
    client_id: client.client_id,
    name: client.name,
    company: client.company,
    industry: client.industry,
    status: client.status,
    owner: client.assigned_account_manager?.full_name ?? "Unassigned",
    lastMeeting: formatDate(client.last_call_at),
  })),
);

const total = computed(() => data.value?.meta?.total ?? 0);
const rangeStart = computed(() =>
  total.value === 0 ? 0 : (page.value - 1) * limit.value + 1,
);
const rangeEnd = computed(() =>
  Math.min(page.value * limit.value, total.value),
);
</script>