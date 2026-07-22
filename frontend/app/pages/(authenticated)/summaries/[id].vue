<template>
  <main class="mx-auto max-w-4xl space-y-6 p-6 lg:p-8">
    <UButton
      to="/summaries"
      icon="i-lucide-arrow-left"
      color="neutral"
      variant="link"
      class="-ml-2"
      >Back to summaries</UButton
    >
    <section class="rounded-2xl bg-black p-6 text-white">
      <p class="text-sm text-[#e0b818]">Discovery meeting · Jul 15, 2026</p>
      <h1 class="mt-1 text-3xl font-semibold">Holiday campaign discovery</h1>
      <p class="mt-3 text-sm text-neutral-300">
        Mawingu Retail · Processed from Fathom transcript by Kora AI
      </p>
    </section>
    <div class="grid gap-6 md:grid-cols-3">
      <UCard
        v-for="group in groups"
        :key="group.title"
        :ui="{ root: 'ring-0 border border-neutral-200 shadow-sm' }"
        ><template #header
          ><div class="flex items-center gap-2">
            <UIcon :name="group.icon" class="text-[#c59d00]" />
            <h2 class="font-semibold text-neutral-950">{{ group.title }}</h2>
          </div></template
        >
        <ul class="space-y-3">
          <li
            v-for="item in group.items"
            :key="item"
            class="text-sm leading-6 text-neutral-600"
          >
            {{ item }}
          </li>
        </ul></UCard
      >
    </div>
    <UCard :ui="{ root: 'ring-0 border border-neutral-200 shadow-sm' }"
      ><template #header
        ><h2 class="font-semibold text-neutral-950">
          Suggested follow-up questions
        </h2></template
      >
      <ol class="space-y-3">
        <li
          v-for="(question, index) in questions"
          :key="question"
          class="flex gap-3 text-sm text-neutral-700"
        >
          <span
            class="flex size-6 shrink-0 items-center justify-center rounded-full bg-yellow-100 text-xs font-semibold text-yellow-800"
            >{{ index + 1 }}</span
          >{{ question }}
        </li>
      </ol></UCard
    >
  </main>
</template>
<script setup lang="ts">
const groups = [
  {
    title: "Objectives",
    icon: "i-lucide-target",
    items: [
      "Increase holiday revenue through a unified customer journey.",
      "Improve conversion from social campaigns into purchases.",
    ],
  },
  {
    title: "Pain points",
    icon: "i-lucide-triangle-alert",
    items: [
      "Campaign performance is fragmented across teams.",
      "Store and ecommerce experiences feel disconnected.",
    ],
  },
  {
    title: "Requirements",
    icon: "i-lucide-list-checks",
    items: [
      "Phased delivery before the holiday campaign.",
      "Leadership needs measurable conversion reporting.",
    ],
  },
];
const questions = [
  "Which campaign and conversion metrics will define a successful launch?",
  "Who are the final decision-makers for the experience direction?",
  "What data and customer research can the team access in week one?",
];
</script>
