<template>
  <UCard :ui="{ root: 'ring-0 border border-neutral-200 !bg-white shadow-sm' }">
    <template #header>
      <h2 class="font-semibold text-neutral-950">Requirements</h2>
    </template>

    <ul v-if="items.length" class="space-y-2">
      <li
        v-for="(item, i) in items"
        :key="i"
        class="flex items-center gap-2"
      >
        <UCheckbox
          :model-value="item.checked"
          :disabled="saving"
          @update:model-value="(checked) => toggle(i, !!checked)"
        />
        <span
          class="flex-1 text-sm text-neutral-700"
          :class="{ 'text-neutral-400 line-through': item.checked }"
        >
          {{ item.text }}
        </span>
        <UButton
          icon="i-lucide-trash-2"
          color="error"
          variant="ghost"
          size="xs"
          :disabled="saving"
          @click="remove(i)"
        />
      </li>
    </ul>
    <p v-else class="text-sm text-neutral-500">No requirements captured yet.</p>

    <form class="mt-4 flex gap-2" @submit.prevent="add">
      <UInput
        v-model="draft"
        placeholder="Add a requirement"
        class="w-full"
        :disabled="saving"
        :ui="{ base: 'bg-white text-neutral-900 ring-neutral-200 focus:ring-2 focus:ring-[#e0b818]' }"
      />
      <UButton type="submit" color="neutral" variant="outline" :disabled="saving || !draft.trim()">
        Add
      </UButton>
    </form>
  </UCard>
</template>

<script setup lang="ts">
interface RequirementItem {
  text: string;
  checked: boolean;
}

const props = defineProps<{
  proposal: any;
}>();

const emit = defineEmits<{
  saved: [proposal: any];
}>();

const toast = useToast();
const authStore = useAuthStore();
const saving = ref(false);
const draft = ref("");

const items = computed<RequirementItem[]>(() => props.proposal?.requirements_checklist ?? []);

async function persist(next: RequirementItem[]) {
  if (!props.proposal?.proposal_id) return;

  saving.value = true;
  try {
    const response = await $fetch<{ success: boolean; data: any }>(
      `/api/proposals/${props.proposal.proposal_id}`,
      {
        method: "PATCH",
        body: { requirements_checklist: next, user_id: authStore.user?.user_id },
      },
    );
    emit("saved", { ...props.proposal, ...response.data });
  } catch (error: any) {
    toast.add({
      title: "Couldn't update requirements",
      description: error?.data?.message ?? error?.message ?? "Something went wrong.",
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    saving.value = false;
  }
}

function toggle(index: number, checked: boolean) {
  const next = items.value.map((item, i) => (i === index ? { ...item, checked } : item));
  persist(next);
}

function remove(index: number) {
  const next = items.value.filter((_, i) => i !== index);
  persist(next);
}

function add() {
  const text = draft.value.trim();
  if (!text) return;
  persist([...items.value, { text, checked: false }]);
  draft.value = "";
}
</script>
