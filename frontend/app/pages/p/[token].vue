<template>
  <div class="min-h-screen bg-neutral-50">
    <header class="border-b border-neutral-200 bg-black px-6 py-4">
      <div class="mx-auto flex max-w-4xl items-center gap-3">
        <AppLogoMark class="size-8 shrink-0" />
        <span class="text-sm font-semibold tracking-tight text-white">Kora AI</span>
      </div>
    </header>

    <main class="mx-auto max-w-4xl space-y-6 p-6 lg:p-8">
      <div v-if="pending" class="space-y-6">
        <USkeleton class="h-32 w-full rounded-2xl bg-neutral-200" />
        <USkeleton class="h-64 w-full rounded-2xl bg-neutral-200" />
      </div>

      <div v-else-if="error" class="rounded-2xl border border-neutral-200 bg-white p-10 text-center">
        <UIcon name="i-lucide-file-x" class="mx-auto mb-3 size-10 text-neutral-300" />
        <p class="font-medium text-neutral-900">This link isn't valid or has expired.</p>
        <p class="mt-1 text-sm text-neutral-500">
          Please reach out to whoever sent it for a fresh copy.
        </p>
      </div>

      <template v-else-if="proposal">
        <section class="rounded-2xl bg-black p-6 text-white">
          <p class="text-sm text-[#e0b818]">Proposal for {{ proposal.client?.company || "you" }}</p>
          <h1 class="mt-1 text-2xl font-semibold">
            {{ proposal.scope_of_work?.split(".")[0] || "Your proposal" }}
          </h1>
          <p class="mt-2 text-sm text-neutral-300">
            Prepared by Kora AI · {{ formatDate(proposal.created_at) }}
          </p>
        </section>

        <UCard :ui="{ root: 'ring-0 border border-neutral-200 !bg-white shadow-sm' }">
          <template #header>
            <h2 class="font-semibold text-neutral-950">Scope of work</h2>
          </template>
          <p class="whitespace-pre-line text-sm leading-7 text-neutral-600">
            {{ proposal.scope_of_work || "Not yet established." }}
          </p>
        </UCard>

        <UCard :ui="{ root: 'ring-0 border border-neutral-200 !bg-white shadow-sm' }">
          <template #header>
            <h2 class="font-semibold text-neutral-950">Deliverables</h2>
          </template>
          <ul v-if="proposal.deliverables?.length" class="space-y-2">
            <li
              v-for="(item, i) in proposal.deliverables"
              :key="i"
              class="flex gap-2 text-sm text-neutral-700"
            >
              <span class="text-[#c59d00]">•</span>{{ item }}
            </li>
          </ul>
          <p v-else class="text-sm text-neutral-500">Not yet established.</p>
        </UCard>

        <UCard :ui="{ root: 'ring-0 border border-neutral-200 !bg-white shadow-sm' }">
          <template #header>
            <h2 class="font-semibold text-neutral-950">Timeline</h2>
          </template>
          <p class="text-sm leading-6 text-neutral-700">
            {{ proposal.timeline || "Not yet established." }}
          </p>
        </UCard>

        <UCard
          v-for="quote in proposal.quotes"
          :key="quote.quote_id"
          :ui="{ root: 'ring-0 border border-neutral-200 !bg-white shadow-sm' }"
        >
          <template #header>
            <h2 class="font-semibold text-neutral-950">Quotation</h2>
          </template>
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
          </div>
          <div class="ml-auto mt-6 max-w-xs space-y-3 border-t border-neutral-200 pt-5 text-sm">
            <div class="flex justify-between text-neutral-500">
              <span>Subtotal</span>
              <span>{{ quote.currency }} {{ formatNumber(quote.subtotal) }}</span>
            </div>
            <div class="flex justify-between text-neutral-500">
              <span>Tax ({{ quote.tax_rate }}%)</span>
              <span>{{ quote.currency }} {{ formatNumber((quote.subtotal * quote.tax_rate) / 100) }}</span>
            </div>
            <div v-if="quote.discount_amount" class="flex justify-between text-neutral-500">
              <span>Discount</span>
              <span>-{{ quote.currency }} {{ formatNumber(quote.discount_amount) }}</span>
            </div>
            <div class="flex justify-between text-lg font-semibold text-neutral-950">
              <span>Total</span>
              <span>{{ quote.currency }} {{ formatNumber(quote.total) }}</span>
            </div>
          </div>
        </UCard>
      </template>
    </main>

    <footer class="pb-10 text-center text-xs text-neutral-400">
      Generated by Kora AI
    </footer>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ public: true, layout: false });

const route = useRoute();
const token = route.params.token as string;

const {
  data: proposal,
  pending,
  error,
} = await useLazyFetch<any>(`/api/public/proposals/${token}`);

function formatDate(iso: string) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatNumber(n: number) {
  return Number(n ?? 0).toLocaleString();
}
</script>
