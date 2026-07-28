<template>
  <UModal v-model:open="open" :dismissible="!sending" :ui="{ content: 'max-w-4xl' }">
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
                <h2 class="text-lg font-semibold text-neutral-950">Send proposal</h2>
                <p class="text-sm text-neutral-500">
                  Review exactly what the client will see, then send.
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
            <div class="grid gap-6 p-6 md:grid-cols-2">
              <div class="space-y-4">
                <UFormField name="to_email" label="Recipient email" required>
                  <UInput
                    v-model="form.to_email"
                    icon="i-lucide-mail"
                    type="email"
                    placeholder="client@company.com"
                    class="w-full"
                    :ui="{ base: FIELD_BASE }"
                  />
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
                    :rows="6"
                    class="w-full"
                    :ui="{ base: FIELD_BASE }"
                  />
                </UFormField>

                <p class="text-xs text-neutral-500">
                  The client gets a link to a read-only page with the full proposal
                  and quotation — no login required.
                </p>
              </div>

              <div class="space-y-2">
                <p class="text-xs font-semibold uppercase tracking-wider text-neutral-400">
                  Preview
                </p>
                <div class="overflow-hidden rounded-xl border border-neutral-200">
                  <iframe
                    v-if="proposal?.proposal_html"
                    :srcdoc="proposal.proposal_html"
                    class="h-[420px] w-full bg-white"
                  />
                  <div v-else class="space-y-3 bg-neutral-50 p-5">
                    <p class="font-medium text-neutral-900">
                      {{ proposal?.client?.company || "Untitled client" }}
                    </p>
                    <p class="line-clamp-6 text-sm text-neutral-600">
                      {{ proposal?.scope_of_work || "No scope of work yet." }}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div class="flex justify-end gap-3 border-t border-neutral-100 px-6 py-4">
              <UButton color="neutral" variant="soft" :disabled="sending" @click="open = false">
                Cancel
              </UButton>
              <UButton type="submit" color="primary" class="text-white" :loading="sending">
                Send proposal
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
  proposal: any | null;
}>();

const emit = defineEmits<{
  sent: [proposal: any];
}>();

const toast = useToast();
const authStore = useAuthStore();
const sending = ref(false);

const schema = v.object({
  to_email: v.pipe(v.string(), v.email("Enter a valid email")),
  subject: v.pipe(v.string(), v.minLength(1, "Subject is required")),
  message: v.optional(v.string()),
});

const form = reactive({
  to_email: "",
  subject: "",
  message: "",
});

watch(
  () => props.proposal,
  (proposal) => {
    const company = proposal?.client?.company || "your project";
    form.to_email = proposal?.client?.email || "";
    form.subject = `Your proposal from Tafsiri — ${company}`;
    form.message =
      "Please find your proposal ready for review. Click below to view the full scope, timeline, and pricing.";
  },
  { immediate: true },
);

async function send() {
  if (!props.proposal?.proposal_id) return;

  sending.value = true;
  try {
    const response = await $fetch<{ success: boolean; data: any }>(
      `/api/proposals/${props.proposal.proposal_id}/send`,
      {
        method: "POST",
        body: {
          to_email: form.to_email,
          subject: form.subject,
          message: form.message,
          user_id: authStore.user?.user_id,
        },
      },
    );

    emit("sent", response.data);
    open.value = false;

    toast.add({
      title: "Proposal sent",
      description: `Emailed to ${form.to_email}.`,
      color: "success",
      icon: "i-lucide-circle-check",
    });
  } catch (error: any) {
    toast.add({
      title: "Couldn't send the proposal",
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
