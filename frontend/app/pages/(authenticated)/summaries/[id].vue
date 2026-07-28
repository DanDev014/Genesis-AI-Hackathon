<template>
  <main class="mx-auto max-w-4xl space-y-6 p-6 lg:p-8">
    <UButton
      to="/summaries"
      icon="i-lucide-arrow-left"
      color="neutral"
      variant="link"
      class="-ml-2"
    >
      Back to summaries
    </UButton>

    <div v-if="pending" class="space-y-6">
      <USkeleton class="h-28 w-full rounded-2xl bg-neutral-200" />
      <USkeleton class="h-96 w-full rounded-2xl bg-neutral-200" />
    </div>

    <p v-else-if="error" class="text-sm text-red-600">
      Couldn't load this summary. Please try again.
    </p>

    <template v-else-if="summary">
      <section class="flex flex-col justify-between gap-4 rounded-2xl bg-black p-6 text-white md:flex-row md:items-start">
        <div>
          <p class="text-sm text-[#e0b818]">
            {{ meeting?.meeting_type || "Meeting" }} · {{ formatDate(summary.created_at) }}
          </p>
          <h1 class="mt-1 text-3xl font-semibold">
            {{ meeting?.title || "Untitled meeting" }}
          </h1>
          <p class="mt-3 text-sm text-neutral-300">
            {{ meeting?.key_points?.client?.company || "—" }} · Processed by Tafsiri
          </p>
        </div>
        <UButton icon="i-lucide-send" class="text-white" @click="sendOpen = true">
          Send to team
        </UButton>
      </section>

      <UCard :ui="{ root: 'ring-0 border border-neutral-200 !bg-white shadow-sm' }">
        <MeetingKeyPoints :meeting="meeting" />
      </UCard>
    </template>

    <SendSummaryModal
      v-model="sendOpen"
      :summary="summary"
      @sent="onSent"
    />
  </main>
</template>

<script setup lang="ts">
const route = useRoute();
const summaryId = route.params.id as string;

const sendOpen = ref(false);

const {
  data: response,
  pending,
  error,
  refresh,
} = await useLazyFetch<{ success: boolean; data: any }>(`/api/summaries/${summaryId}`);

const summary = computed(() => response.value?.data ?? null);
const meeting = computed(() => summary.value?.first_meeting_deliverables ?? null);

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

async function onSent() {
  await refresh();
}
</script>
