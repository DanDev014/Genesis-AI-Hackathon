<template>
  <UModal v-model:open="open" :dismissible="!saving" :ui="{ content: 'max-w-2xl' }">
    <template #content>
      <UCard
        :ui="{
          root: 'border-0 shadow-none bg-white',
          header: 'px-6 py-4 border-b bg-white',
          footer: 'px-6 py-4 border-t bg-white',
        }"
      >
        <template #header>
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold text-neutral-950">Edit proposal</h2>
            <UButton
              color="neutral"
              variant="ghost"
              icon="i-lucide-x"
              :disabled="saving"
              @click="open = false"
            />
          </div>
        </template>

        <UForm :schema="schema" :state="form" class="space-y-5" @submit="save">
          <fieldset :disabled="saving" class="space-y-5">
            <UFormField name="scope_of_work" label="Scope of work" required>
              <UTextarea
                v-model="form.scope_of_work"
                :rows="4"
                class="w-full"
                :ui="{ base: FIELD_BASE }"
              />
            </UFormField>

            <UFormField name="timeline" label="Timeline">
              <UInput v-model="form.timeline" class="w-full" :ui="{ base: FIELD_BASE }" />
            </UFormField>

            <UFormField name="status" label="Status" required>
              <USelectMenu
                v-model="form.status"
                :items="statuses"
                class="w-full"
                :ui="{ base: FIELD_BASE }"
              />
            </UFormField>

            <UFormField label="Deliverables">
              <div class="space-y-2">
                <div v-for="(_, i) in form.deliverables" :key="i" class="flex gap-2">
                  <UInput
                    v-model="form.deliverables[i]"
                    class="w-full"
                    placeholder="Deliverable"
                    :ui="{ base: FIELD_BASE }"
                  />
                  <UButton
                    icon="i-lucide-trash-2"
                    color="error"
                    variant="ghost"
                    @click="form.deliverables.splice(i, 1)"
                  />
                </div>

                <UButton
                  icon="i-lucide-plus"
                  color="neutral"
                  variant="outline"
                  size="xs"
                  @click="form.deliverables.push('')"
                >
                  Add deliverable
                </UButton>
              </div>
            </UFormField>

            <div class="flex justify-end gap-3 pt-2">
              <UButton color="neutral" variant="soft" :disabled="saving" @click="open = false">
                Cancel
              </UButton>

              <UButton type="submit" color="primary" :loading="saving">
                Save changes
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

// Nuxt UI's default field background renders dark in this app's theme —
// every field needs this override, same as kora-ai.vue's inputs.
const FIELD_BASE =
  "bg-white text-neutral-900 ring-neutral-200 focus:ring-2 focus:ring-[#e0b818]";

const open = defineModel<boolean>({ default: false });

const props = defineProps<{
  proposal: any;
}>();

const emit = defineEmits<{
  saved: [proposal: any];
}>();

const toast = useToast();
const saving = ref(false);

const statuses = ["draft", "sent", "revised", "accepted", "rejected"];

const schema = v.object({
  scope_of_work: v.pipe(v.string(), v.minLength(1, "Scope of work is required")),
  timeline: v.optional(v.string()),
  status: v.pipe(v.string(), v.minLength(1, "Status is required")),
});

const form = reactive({
  scope_of_work: "",
  timeline: "",
  status: "draft",
  deliverables: [] as string[],
});

watch(
  () => props.proposal,
  (proposal) => {
    form.scope_of_work = proposal?.scope_of_work ?? "";
    form.timeline = proposal?.timeline ?? "";
    form.status = proposal?.status ?? "draft";
    form.deliverables = [...(proposal?.deliverables ?? [])];
  },
  { immediate: true },
);

async function save() {
  if (!props.proposal?.proposal_id) return;

  saving.value = true;
  try {
    const response = await $fetch<{ success: boolean; data: Record<string, any> }>(
      `/api/proposals/${props.proposal.proposal_id}`,
      {
        method: "PATCH",
        body: {
          scope_of_work: form.scope_of_work,
          timeline_milestones: form.timeline,
          status: form.status,
          deliverables_list: form.deliverables.filter((d) => d.trim()),
        },
      },
    );

    emit("saved", { ...response.data, proposal_html: props.proposal.proposal_html });
    open.value = false;

    toast.add({
      title: "Proposal updated",
      color: "success",
      icon: "i-lucide-circle-check",
    });
  } catch (error: any) {
    toast.add({
      title: "Update failed",
      description: error?.data?.message ?? error?.message ?? "Something went wrong.",
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    saving.value = false;
  }
}
</script>
