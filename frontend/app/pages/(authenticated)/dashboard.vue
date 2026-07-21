<template>
  <main class="space-y-8 p-6 lg:p-8">
    <section class="flex flex-col justify-between gap-5 md:flex-row md:items-end">
      <div>
        <p class="text-sm font-medium text-yellow-700">Workspace overview</p>
        <h1 class="mt-1 text-3xl font-semibold tracking-tight text-neutral-950">Good morning, Genesis team.</h1>
        <p class="mt-2 max-w-2xl text-neutral-500">Track every client conversation from discovery to approved proposal in one calm, shared workspace.</p>
      </div>
      <UButton to="/kora-ai" icon="i-lucide-sparkles" class="bg-[#e0b818] px-5 font-semibold text-black hover:bg-yellow-400">
        Process a meeting
      </UButton>
    </section>

    <section class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <MetricCard label="Active clients" value="24" detail="4 added this month" icon="i-lucide-building-2" />
      <MetricCard label="Meetings processed" value="38" detail="92% transcription coverage" icon="i-lucide-audio-lines" />
      <MetricCard label="Proposals in review" value="7" detail="KES 4.2M potential value" icon="i-lucide-file-check-2" />
      <MetricCard label="Win rate" value="64%" detail="Up 8% from last quarter" icon="i-lucide-trending-up" />
    </section>

    <section class="grid gap-6 xl:grid-cols-5">
      <UCard class="xl:col-span-3" :ui="{ root: 'ring-0 border border-neutral-200 bg-white shadow-sm' }">
        <template #header>
          <div class="flex items-center justify-between">
            <div>
              <h2 class="font-semibold text-neutral-950">Pipeline movement</h2>
              <p class="mt-1 text-sm text-neutral-500">Client value by stage this month</p>
            </div>
            <UBadge color="neutral" variant="soft">July 2026</UBadge>
          </div>
        </template>
        <div class="flex h-72 items-end gap-4 px-2 pt-4">
          <div v-for="stage in pipeline" :key="stage.label" class="flex flex-1 flex-col items-center gap-3">
            <div class="flex h-52 w-full items-end rounded-t-xl bg-neutral-100 px-2">
              <div class="w-full rounded-t-lg bg-[#e0b818] transition-all" :style="{ height: `${stage.value}%` }" />
            </div>
            <div class="text-center">
              <p class="text-xs font-medium text-neutral-700">{{ stage.label }}</p>
              <p class="mt-1 text-xs text-neutral-500">{{ stage.amount }}</p>
            </div>
          </div>
        </div>
      </UCard>

      <UCard class="xl:col-span-2" :ui="{ root: 'ring-0 border border-neutral-200 bg-black text-white shadow-sm' }">
        <template #header>
          <div class="flex items-center gap-2">
            <span class="flex size-8 items-center justify-center rounded-lg bg-[#e0b818] text-black"><UIcon name="i-lucide-sparkles" /></span>
            <div><h2 class="font-semibold">Kora AI</h2><p class="text-xs text-neutral-400">Meeting intelligence</p></div>
          </div>
        </template>
        <div class="space-y-5">
          <p class="text-sm leading-6 text-neutral-300">Drop in a Fathom transcript to produce a discovery summary or a proposal-ready strategy pack.</p>
          <div class="space-y-3">
            <div v-for="item in aiTasks" :key="item.title" class="flex items-center gap-3 rounded-xl border border-neutral-800 bg-neutral-900 p-3">
              <UIcon :name="item.icon" class="size-4 text-[#e0b818]" />
              <div class="min-w-0 flex-1"><p class="text-sm font-medium">{{ item.title }}</p><p class="text-xs text-neutral-400">{{ item.detail }}</p></div>
              <span class="size-2 rounded-full bg-emerald-400" />
            </div>
          </div>
          <UButton to="/kora-ai" block class="bg-[#e0b818] font-semibold text-black hover:bg-yellow-400">Open AI workspace</UButton>
        </div>
      </UCard>
    </section>

    <section class="grid gap-6 xl:grid-cols-5">
      <div class="xl:col-span-3"><div class="mb-4 flex items-center justify-between"><div><h2 class="font-semibold text-neutral-950">Recent client activity</h2><p class="text-sm text-neutral-500">Latest movement across the pipeline</p></div><UButton to="/clients" variant="link" color="neutral">View clients</UButton></div><DataTable :columns="activityColumns" :rows="activities" row-key="id"><template #cell-client="{ row }"><div><p class="font-medium text-neutral-900">{{ row.client }}</p><p class="text-xs text-neutral-500">{{ row.company }}</p></div></template><template #cell-status="{ row }"><UBadge color="warning" variant="subtle">{{ row.status }}</UBadge></template></DataTable></div>
      <UCard class="xl:col-span-2" :ui="{ root: 'ring-0 border border-neutral-200 bg-white shadow-sm' }"><template #header><h2 class="font-semibold text-neutral-950">Next actions</h2></template><div class="space-y-4"><div v-for="action in actions" :key="action.title" class="flex gap-3"><span class="mt-1 flex size-7 shrink-0 items-center justify-center rounded-full bg-yellow-100 text-yellow-800"><UIcon :name="action.icon" class="size-4" /></span><div><p class="text-sm font-medium text-neutral-900">{{ action.title }}</p><p class="mt-1 text-xs text-neutral-500">{{ action.detail }}</p></div></div></div></UCard>
    </section>
  </main>
</template>

<script setup lang="ts">
const pipeline = [{ label: 'Discovery', value: 38, amount: 'KES 1.8M' }, { label: 'Strategy', value: 58, amount: 'KES 2.6M' }, { label: 'Proposal', value: 78, amount: 'KES 4.2M' }, { label: 'Won', value: 51, amount: 'KES 2.1M' }];
const aiTasks = [{ title: '3 discovery calls', detail: 'Ready for a summary', icon: 'i-lucide-file-text' }, { title: '2 strategy sessions', detail: 'Ready for proposal drafting', icon: 'i-lucide-sparkles' }];
const activityColumns = [{ key: 'client', label: 'Client' }, { key: 'activity', label: 'Activity' }, { key: 'status', label: 'Status' }, { key: 'time', label: 'Updated' }];
const activities = [{ id: 1, client: 'Amina Njeri', company: 'Mawingu Retail', activity: 'Strategy meeting processed', status: 'Ready for proposal', time: '12 min ago' }, { id: 2, client: 'David Otieno', company: 'Nuru Logistics', activity: 'Proposal reviewed', status: 'Needs approval', time: '1 hour ago' }, { id: 3, client: 'Lina Wanjiku', company: 'Cedar Health', activity: 'Discovery transcript uploaded', status: 'Summary pending', time: '3 hours ago' }];
const actions = [{ title: 'Review Nuru Logistics proposal', detail: 'Due today · KES 1,250,000', icon: 'i-lucide-file-check-2' }, { title: 'Follow up with Mawingu Retail', detail: 'Discovery questions remain', icon: 'i-lucide-message-square' }, { title: 'Send Cedar Health quotation', detail: 'Approved 2 hours ago', icon: 'i-lucide-send' }];
</script>
