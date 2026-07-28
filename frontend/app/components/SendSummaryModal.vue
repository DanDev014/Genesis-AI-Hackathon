<template>
  <UModal v-model:open="open" :dismissible="!sending" :ui="{ content: 'max-w-lg' }">
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
              @click="open = false"
            />
          </div>
        </template>

        <UForm :schema="schema" :state="form" @submit="send">
          <fieldset :disabled="sending">
            <div class="space-y-4 p-6">
              <UFormField name="to_emails" label="Recipients" required>
                <UInput
                  v-model="form.to_emails"
                  icon="i-lucide-users"
                  placeholder="daniel@agency.com, kevin@agency.com"
                  class="w-full"
                  :ui="{ base: FIELD_BASE }"
                />
                <p class="mt-1 text-xs text-neutral-500">
                  Comma-separated — sends one email to everyone at once.
                </p>
              </UFormField>

              <UFormField name="subject" label="Subject" required>
                <UInput
                  v-model="form.subject"
                  class="w-full"
                  :ui="{ base: FIELD_BASE }"
                />
              </UFormField>

              <UFormField name="message" label="Message">
                <UTextarea
                  v-model="form.message"
                  :rows="5"
                  class="w-full"
                  :ui="{ base: FIELD_BASE }"
                />
              </UFormField>
            </div>

            <div class="flex justify-end gap-3 border-t border-neutral-100 px-6 py-4">
              <UButton color="neutral" variant="soft" :disabled="sending" @click="open = false">
                Cancel
              </UButton>
              <UButton type="submit" color="primary" class="text-white" :loading="sending">
                Send to team
              </UButton>
            </div>
          </fieldset>
        </UForm>
      </UCard>
    </template>
  </UModal>
</template>

<script setup lang="ts">
import * as v from "valibot";

const FIELD_BASE =
  "bg-white text-neutral-900 ring-neutral-200 focus:ring-2 focus:ring-[#e0b818]";

const open = defineModel<boolean>({ default: false });

const props = defineProps<{
  summary: any | null;
}>();

const emit = defineEmits<{
  sent: [summary: any];
}>();

const toast = useToast();
const sending = ref(false);

const schema = v.object({
  to_emails: v.pipe(v.string(), v.minLength(1, "At least one recipient is required")),
  subject: v.pipe(v.string(), v.minLength(1, "Subject is required")),
  message: v.optional(v.string()),
});

const form = reactive({
  to_emails: "",
  subject: "",
  message: "",
});

watch(
  () => props.summary,
  (summary) => {
    const meeting = summary?.first_meeting_deliverables;
    const company = meeting?.key_points?.client?.company ?? meeting?.client?.company ?? "a client";
    form.subject = `Discovery call summary — ${company}`;
    form.message =
      "The discovery call has been processed. Click below to see the full summary, key points, and open questions.";
  },
  { immediate: true },
);

async function send() {
  if (!props.summary?.summary_id) return;

  const to_emails = form.to_emails
    .split(",")
    .map((e) => e.trim())
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
    const response = await $fetch<{ success: boolean; data: any }>(
      `/api/summaries/${props.summary.summary_id}/send`,
      {
        method: "POST",
        body: {
          to_emails,
          subject: form.subject,
          message: form.message,
        },
      },
    );

    emit("sent", response.data);
    open.value = false;

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
