<template>
  <main class="mx-auto max-w-4xl space-y-6 p-6 lg:p-8">
    <UButton
      to="/quotations"
      icon="i-lucide-arrow-left"
      color="neutral"
      variant="link"
      class="-ml-2"
    >
      Back to quotations
    </UButton>

    <div v-if="pending" class="space-y-6">
      <USkeleton class="h-28 w-full rounded-2xl bg-neutral-200" />
      <USkeleton class="h-64 w-full rounded-2xl bg-neutral-200" />
    </div>

    <p v-else-if="error" class="text-sm text-red-600">
      Couldn't load this quotation. Please try again.
    </p>

    <template v-else-if="quote">
      <section
        class="flex flex-col justify-between gap-4 rounded-2xl bg-black p-6 text-white sm:flex-row"
      >
        <div>
          <p class="text-sm text-[#e0b818]">Quotation #{{ quote.quote_id }}</p>
          <h1 class="mt-1 text-3xl font-semibold">
            {{ quote.proposal?.client?.company || "Untitled client" }}
          </h1>
          <p class="mt-2 text-sm text-neutral-300">
            Linked to proposal #{{ quote.proposal?.proposal_id ?? "—" }} · Valid for
            {{ quote.validity_days }} days
          </p>
        </div>
        <div class="flex items-center gap-3">
          <UBadge :color="statusColor(quote.status)" variant="subtle">
            {{ quote.status }}
          </UBadge>
          <UTooltip :text="quote.proposal?.approved ? '' : 'Approve the linked proposal first'">
            <UButton
              icon="i-lucide-banknote"
              color="neutral"
              :class="quote.proposal?.approved ? 'text-white' : ''"
              :disabled="!quote.proposal?.approved"
              :loading="sendingToQb"
              @click="sendToQuickBooks"
            >
              Send to QuickBooks
            </UButton>
          </UTooltip>
          <UButton icon="i-lucide-pencil" class="text-white" @click="editOpen = true">
            Edit quotation
          </UButton>
        </div>
      </section>

      <UCard :ui="{ root: 'ring-0 border border-neutral-200 !bg-white shadow-sm' }">
        <div class="divide-y divide-neutral-100">
          <div
            v-for="(item, i) in quote.line_items"
            :key="i"
            class="flex items-center justify-between gap-4 py-4 first:pt-0 last:pb-0"
          >
            <div>
              <p class="font-medium text-neutral-900">{{ item.item }}</p>
              <p class="mt-1 text-sm text-neutral-500">
                Qty {{ item.qty }} × {{ quote.currency }} {{ formatNumber(item.unit_price) }}
              </p>
            </div>
            <p class="font-medium text-neutral-900">
              {{ quote.currency }} {{ formatNumber(item.amount) }}
            </p>
          </div>
          <p v-if="!quote.line_items?.length" class="py-4 text-sm text-neutral-500">
            No line items yet.
          </p>
        </div>
        <div class="ml-auto mt-6 max-w-xs space-y-3 border-t border-neutral-200 pt-5 text-sm">
          <div class="flex justify-between text-neutral-500">
            <span>Subtotal</span>
            <span>{{ quote.currency }} {{ formatNumber(quote.subtotal) }}</span>
          </div>
          <div class="flex justify-between text-neutral-500">
            <span>Tax ({{ quote.tax_rate }}%)</span>
            <span>{{ quote.currency }} {{ formatNumber(taxAmount) }}</span>
          </div>
          <div v-if="quote.discount_amount" class="flex justify-between text-neutral-500">
            <span>Discount</span>
            <span>-{{ quote.currency }} {{ formatNumber(quote.discount_amount) }}</span>
          </div>
          <div class="flex justify-between text-lg font-semibold text-neutral-950">
            <span>Total</span>
            <span>{{ quote.currency }} {{ formatNumber(quote.total ?? quote.total_amount) }}</span>
          </div>
        </div>
      </UCard>

      <UCard
        v-if="quote.quickbooks_result"
        :ui="{ root: 'ring-0 border border-neutral-200 !bg-white shadow-sm' }"
      >
        <template #header>
          <h2 class="font-semibold text-neutral-950">QuickBooks</h2>
        </template>
        <p v-if="quote.quickbooks_result.ok" class="text-sm text-neutral-700">
          Sent ({{ quote.quickbooks_result.mode }}) — Estimate
          {{ quote.quickbooks_result.response?.Estimate?.Id }}
        </p>
        <p v-else class="text-sm text-red-600">
          Failed ({{ quote.quickbooks_result.mode }}): {{ quote.quickbooks_result.error }}
        </p>
      </UCard>
    </template>

    <EditQuotationModal v-model="editOpen" :quotation="quote" @saved="onSaved" />
  </main>
</template>

<script setup lang="ts">
const route = useRoute();
const quoteId = route.params.id as string;

const editOpen = ref(false);
const sendingToQb = ref(false);

const toast = useToast();
const authStore = useAuthStore();

const {
  data: quote,
  pending,
  error,
  refresh,
} = await useLazyFetch<any>(`/api/quotes/${quoteId}`);

function statusColor(status: string) {
  if (status === "accepted") return "success";
  if (status === "sent") return "warning";
  if (status === "expired") return "error";
  return "neutral";
}

function formatNumber(n: number) {
  return Number(n ?? 0).toLocaleString();
}

const taxAmount = computed(() => {
  const subtotal = Number(quote.value?.subtotal ?? 0);
  const rate = Number(quote.value?.tax_rate ?? 0);
  return (subtotal * rate) / 100;
});

async function onSaved(updated: any) {
  quote.value = updated;
  await refresh();
}

async function sendToQuickBooks() {
  if (!quote.value?.quote_id) return;

  sendingToQb.value = true;
  try {
    const response = await $fetch<{ success: boolean; data: any }>(
      `/api/quotes/${quote.value.quote_id}/send-to-quickbooks`,
      { method: "POST", body: { user_id: authStore.user?.user_id } },
    );
    quote.value = response.data;
    await refresh();
    toast.add({
      title: response.data.quickbooks_result?.ok ? "Sent to QuickBooks" : "QuickBooks call failed",
      color: response.data.quickbooks_result?.ok ? "success" : "error",
      icon: response.data.quickbooks_result?.ok ? "i-lucide-circle-check" : "i-lucide-circle-alert",
    });
  } catch (error: any) {
    toast.add({
      title: "Couldn't send to QuickBooks",
      description: error?.data?.message ?? error?.data?.error ?? error?.message ?? "Something went wrong.",
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    sendingToQb.value = false;
  }
}
</script>
