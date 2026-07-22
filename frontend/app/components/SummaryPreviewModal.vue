<script setup lang="ts">
import { computed } from "vue";

const open = defineModel<boolean>();

const props = defineProps<{
  summary: any;
}>();

const emit = defineEmits<{
  close: [];
  view: [];
  download: [];
}>();

const meeting = computed(
  () => props.summary?.first_meeting_deliverables ?? null,
);

function close() {
  open.value = false;
  emit("close");
}
</script>

<template>
  <UModal v-model:open="open" :dismissible="false" :ui="{ content: 'max-w-2xl' }">
    <template #content>
      <UCard
        :ui="{
          root: 'border-0 shadow-none !bg-white',
          body: 'p-0 !bg-white',
          header: 'px-6 py-4 border-b !bg-white',
          footer: 'px-6 py-4 border-t !bg-white',
        }"
      >
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <span
                class="flex size-10 shrink-0 items-center justify-center rounded-full bg-success/15 text-success"
              >
                <UIcon name="i-lucide-circle-check-big" class="size-5" />
              </span>
              <div>
                <h2 class="text-lg font-semibold text-neutral-950">Summary generated</h2>
                <p class="text-sm text-neutral-500">
                  Review the generated meeting summary before proceeding.
                </p>
              </div>
            </div>
            <UButton color="neutral" variant="ghost" icon="i-lucide-x" @click="close" />
          </div>
        </template>

        <div class="max-h-[60vh] overflow-y-auto bg-white p-6">
          <MeetingKeyPoints :meeting="meeting" />
        </div>

        <template #footer>
          <div class="flex justify-end gap-3">
            <UButton color="neutral" variant="soft" @click="close">
              Close
            </UButton>

            <UButton
              icon="i-lucide-download"
              color="neutral"
              variant="outline"
              @click="emit('download')"
            >
              Download PDF
            </UButton>

            <UButton
              trailing-icon="i-lucide-arrow-right"
              color="primary"
              class="text-white"
              @click="emit('view')"
            >
              View Summary
            </UButton>
          </div>
        </template>
      </UCard>
    </template>
  </UModal>
</template>
