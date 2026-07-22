<template>
  <main class="mx-auto max-w-4xl space-y-6 p-6 lg:p-8">
    <UButton
      to="/quotes"
      icon="i-lucide-arrow-left"
      color="neutral"
      variant="link"
      class="-ml-2"
      >Back to quotations</UButton
    >
    <section
      class="flex flex-col justify-between gap-4 rounded-2xl bg-black p-6 text-white sm:flex-row"
    >
      <div>
        <p class="text-sm text-[#e0b818]">Quotation QT-1024</p>
        <h1 class="mt-1 text-3xl font-semibold">Mawingu Retail</h1>
        <p class="mt-2 text-sm text-neutral-300">
          Linked to Experience redesign proposal · Valid until Aug 18, 2026
        </p>
      </div>
      <UBadge color="neutral" variant="subtle">Draft</UBadge>
    </section>
    <UCard :ui="{ root: 'ring-0 border border-neutral-200 shadow-sm' }"
      ><div class="divide-y divide-neutral-100">
        <div
          v-for="item in items"
          :key="item.name"
          class="flex items-center justify-between gap-4 py-4 first:pt-0 last:pb-0"
        >
          <div>
            <p class="font-medium text-neutral-900">{{ item.name }}</p>
            <p class="mt-1 text-sm text-neutral-500">{{ item.detail }}</p>
          </div>
          <p class="font-medium text-neutral-900">{{ item.price }}</p>
        </div>
      </div>
      <div
        class="ml-auto mt-6 max-w-xs space-y-3 border-t border-neutral-200 pt-5 text-sm"
      >
        <div class="flex justify-between text-neutral-500">
          <span>Subtotal</span><span>KES 820,000</span>
        </div>
        <div
          class="flex justify-between text-lg font-semibold text-neutral-950"
        >
          <span>Total</span><span>KES 820,000</span>
        </div>
      </div></UCard
    >
    <div class="flex justify-end gap-3">
      <UButton color="neutral" variant="outline">Edit quotation</UButton
      ><UButton
        class="bg-[#e0b818] font-semibold text-black hover:bg-yellow-400"
        icon="i-lucide-send"
        >Send to client</UButton
      >
    </div>
  </main>
</template>
<script setup lang="ts">
const items = [
  {
    name: "Experience audit",
    detail: "Research, journey mapping, and opportunity report",
    price: "KES 180,000",
  },
  {
    name: "Service & storefront redesign",
    detail: "Design direction, prototypes, and design system",
    price: "KES 440,000",
  },
  {
    name: "Implementation handover",
    detail: "Delivery support and team enablement",
    price: "KES 200,000",
  },
];
</script>
