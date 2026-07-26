<template>
  <UModal v-model:open="open" :dismissible="!saving">
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
                <UIcon name="i-lucide-flag" class="size-5" />
              </span>
              <div>
                <h2 class="text-lg font-semibold text-neutral-950">Record outcome</h2>
                <p class="text-sm text-neutral-500">Did we get the job? Log the result and any client feedback.</p>
              </div>
            </div>
            <UButton
              color="neutral"
              variant="ghost"
              icon="i-lucide-x"
              :disabled="saving"
              @click="open = false"
            />
          </div>
        </template>

        <UForm :schema="schema" :state="form" @submit="save">
          <fieldset :disabled="saving">
            <div class="space-y-4 p-6">
              <UFormField name="outcome" label="Outcome" required>
                <div class="flex gap-2">
                  <UButton
                    :color="form.outcome === 'won' ? 'success' : 'neutral'"
                    :variant="form.outcome === 'won' ? 'solid' : 'outline'"
                    icon="i-lucide-circle-check"
                    @click="form.outcome = 'won'"
                  >
                    Won
                  </UButton>
                  <UButton
                    :color="form.outcome === 'lost' ? 'error' : 'neutral'"
                    :variant="form.outcome === 'lost' ? 'solid' : 'outline'"
                    icon="i-lucide-circle-x"
                    @click="form.outcome = 'lost'"
                  >
                    Lost
                  </UButton>
                  <UButton
                    :color="form.outcome === 'pending' ? 'warning' : 'neutral'"
                    :variant="form.outcome === 'pending' ? 'solid' : 'outline'"
                    icon="i-lucide-clock"
                    @click="form.outcome = 'pending'"
                  >
                    Pending
                  </UButton>
                </div>
              </UFormField>

              <UFormField name="notes" label="Client feedback (optional)">
                <UTextarea
                  v-model="form.notes"
                  :rows="4"
                  placeholder="Anything the client said about why, or what tipped the decision..."
                  class="w-full"
                  :ui="{ base: FIELD_BASE }"
                />
              </UFormField>
            </div>

            <div class="flex justify-end gap-3 border-t border-neutral-100 px-6 py-4">
              <UButton color="neutral" variant="soft" :disabled="saving" @click="open = false">
                Cancel
              </UButton>
              <UButton type="submit" color="primary" class="text-white" :loading="saving">
                Save outcome
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
  saved: [proposal: any];
}>();

const toast = useToast();
const authStore = useAuthStore();
const saving = ref(false);

const schema = v.object({
  outcome: v.picklist(["pending", "won", "lost"]),
  notes: v.optional(v.string()),
});

const form = reactive({
  outcome: "pending",
  notes: "",
});

watch(
  () => props.proposal,
  (proposal) => {
    form.outcome = proposal?.outcome || "pending";
    form.notes = proposal?.outcome_notes || "";
  },
  { immediate: true },
);

async function save() {
  if (!props.proposal?.proposal_id) return;

  saving.value = true;
  try {
    const response = await $fetch<{ success: boolean; data: any }>(
      `/api/proposals/${props.proposal.proposal_id}/outcome`,
      {
        method: "POST",
        body: {
          outcome: form.outcome,
          notes: form.notes,
          user_id: authStore.user?.user_id,
        },
      },
    );

    emit("saved", response.data);
    open.value = false;

    toast.add({
      title: "Outcome recorded",
      description: `Marked as ${form.outcome}.`,
      color: "success",
      icon: "i-lucide-circle-check",
    });
  } catch (error: any) {
    toast.add({
      title: "Couldn't save the outcome",
      description:
        error?.data?.message ?? error?.data?.error ?? error?.message ?? "Something went wrong.",
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    saving.value = false;
  }
}
</script>
