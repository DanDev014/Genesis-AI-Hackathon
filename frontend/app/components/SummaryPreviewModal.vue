<script setup lang="ts">
import { computed, reactive, ref } from "vue";

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

// --- Send to team — inlined directly here (not a separate component) so
// there's no cross-component auto-import resolution to go wrong. ---
const toast = useToast();
const sendOpen = ref(false);
const sending = ref(false);

const sendForm = reactive({
  to_emails: "",
  subject: "",
  message: "",
});

function openSend() {
  const company =
    meeting.value?.key_points?.client?.company ?? meeting.value?.client?.company ?? "a client";
  sendForm.subject = `Discovery call summary — ${company}`;
  sendForm.message =
    "The discovery call has been processed. Click below to see the full summary, key points, and open questions.";
  sendOpen.value = true;
}

async function sendToTeam() {
  if (!props.summary?.summary_id) return;

  const to_emails = sendForm.to_emails
    .split(",")
    .map((e: string) => e.trim())
    .filter(Boolean);

  if (!to_emails.length) {
    toast.add({
      title: "Add at least one recipient",
      color: "error",
      icon: "i-lucide-circle-alert",
    });
    return;
  }

  sending.value = true;
  try {
    await $fetch(`/api/summaries/${props.summary.summary_id}/send`, {
      method: "POST",
      body: {
        to_emails,
        subject: sendForm.subject,
        message: sendForm.message,
      },
    });

    sendOpen.value = false;

    toast.add({
      title: "Summary sent",
      description: `Emailed to ${to_emails.length} recipient${to_emails.length > 1 ? "s" : ""}.`,
      color: "success",
      icon: "i-lucide-circle-check",
    });
  } catch (error: any) {
    toast.add({
      title: "Couldn't send the summary",
      description:
        error?.data?.message ?? error?.data?.error ?? error?.message ?? "Something went wrong.",
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    sending.value = false;
  }
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
          <div class="flex flex-wrap justify-end gap-3">
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
              v-if="summary?.summary_id"
              icon="i-lucide-send"
              class="bg-neutral-900 text-white hover:bg-neutral-800"
              @click="openSend"
            >
              Send to team
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

  <UModal v-model:open="sendOpen" :dismissible="!sending" :ui="{ content: 'max-w-lg' }">
    <template #content>
      <UCard
        :ui="{
          root: 'border-0 shadow-none !bg-white',
          header: 'px-6 py-5 border-b !bg-white',
          body: 'p-0 !bg-white',
          footer: 'px-6 py-4 border-t !bg-white',
        }"
      >
        <template #header>
          <div class="flex items-start justify-between gap-4">
            <div class="flex items-center gap-3">
              <span
                class="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary"
              >
                <UIcon name="i-lucide-send" class="size-5" />
              </span>
              <div>
                <h2 class="text-lg font-semibold text-neutral-950">Send to team</h2>
                <p class="text-sm text-neutral-500">
                  Share this discovery call summary with your team.
                </p>
              </div>
            </div>
            <UButton
              color="neutral"
              variant="ghost"
              icon="i-lucide-x"
              :disabled="sending"
              @click="sendOpen = false"
            />
          </div>
        </template>

        <fieldset :disabled="sending">
          <div class="space-y-4 p-6">
            <UFormField name="to_emails" label="Recipients" required>
              <UInput
                v-model="sendForm.to_emails"
                icon="i-lucide-users"
                placeholder="daniel@agency.com, kevin@agency.com"
                class="w-full"
                :ui="{ base: 'bg-white text-neutral-900 ring-neutral-200 focus:ring-2 focus:ring-[#e0b818]' }"
              />
              <p class="mt-1 text-xs text-neutral-500">
                Comma-separated — sends one email to everyone at once.
              </p>
            </UFormField>

            <UFormField name="subject" label="Subject" required>
              <UInput
                v-model="sendForm.subject"
                class="w-full"
                :ui="{ base: 'bg-white text-neutral-900 ring-neutral-200 focus:ring-2 focus:ring-[#e0b818]' }"
              />
            </UFormField>

            <UFormField name="message" label="Message">
              <UTextarea
                v-model="sendForm.message"
                :rows="5"
                class="w-full"
                :ui="{ base: 'bg-white text-neutral-900 ring-neutral-200 focus:ring-2 focus:ring-[#e0b818]' }"
              />
            </UFormField>
          </div>

          <div class="flex justify-end gap-3 border-t border-neutral-100 px-6 py-4">
            <UButton color="neutral" variant="soft" :disabled="sending" @click="sendOpen = false">
              Cancel
            </UButton>
            <UButton
              class="bg-neutral-900 text-white hover:bg-neutral-800"
              :loading="sending"
              @click="sendToTeam"
            >
              Send to team
            </UButton>
          </div>
        </fieldset>
      </UCard>
    </template>
  </UModal>
</template>
