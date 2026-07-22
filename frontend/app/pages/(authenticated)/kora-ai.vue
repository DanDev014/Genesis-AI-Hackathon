<template>
  <main class="mx-auto h-screen p-6">
    <div>
      <p class="text-sm font-medium text-primary">Kora AI workspace</p>
      <h1 class="mt-1 text-xl font-semibold tracking-tight text-neutral-950">
        Turn a Fathom transcript into a summary, proposal and quotations.
      </h1>
      <p class="m-2 text-neutral-500 text-sm">
        Paste a meeting transcript, choose its place in the sales journey, and
        Kora will prepare the right artifact.
      </p>
    </div>
    <div class="grid gap-6 lg:grid-cols-5">
      <UCard
        class="lg:col-span-3"
        :ui="{ root: 'ring-0 border border-neutral-200 bg-white shadow-lg' }"
        ><template #header
          ><div class="flex items-center gap-3">
            <span
              class="flex size-9 items-center justify-center rounded-full bg-primary text-white"
              ><UIcon name="i-lucide-file-text" class="size-5"
            /></span>
            <div>
              <h2 class="font-semibold text-neutral-950">Meeting input</h2>
              <p class="text-sm text-neutral-500">
                Fathom transcript or summary
              </p>
            </div>
          </div></template
        >
        <UForm
          :schema="schema"
          :state="state"
          class="space-y-5 w-full"
          @submit="onSubmit"
        >
          <UFormField name="transcript" label="Transcript" required>
            <UTextarea
              v-model="state.transcript"
              :rows="10"
              class="w-full block"
              placeholder="Paste the Fathom transcript or AI summary here..."
              :ui="{
                root: 'w-full block',
                base: 'bg-white text-neutral-900 ring-neutral-200 w-full block focus:ring-[#e0b818]',
              }"
            />
          </UFormField>
          <div class="grid gap-4 sm:grid-cols-2">
            <UFormField name="meetingType" label="Meeting type" required>
              <USelectMenu
                v-model="state.meetingType"
                :items="meetingTypes"
                placeholder="Select meeting type"
                value-key="value"
                label-key="label"
                class="w-full"
                :ui="{
                  base: 'bg-white text-neutral-900 ring-neutral-200 focus:ring-2 focus:ring-[#e0b818]',
                }"
              />
            </UFormField>
            <UFormField name="clientId" label="Client" required>
              <USelectMenu
                v-model="state.clientId"
                :items="clients"
                value-key="value"
                label-key="label"
                :loading="clientsLoading"
                placeholder="Select a client"
                class="w-full"
                :ui="{
                  base: 'bg-white text-neutral-900 ring-neutral-200 focus:ring-2 focus:ring-[#e0b818]',
                }"
              />
            </UFormField>
          </div>
          <UButton
            block
            type="submit"
            :loading="loading"
            class="bg-primary font-semibold text-white hover:bg-yellow-400"
            icon="i-lucide-sparkles"
          >
            {{
              loading
                ? "Generating..."
                : state.meetingType === "internal"
                  ? "Generate proposal + quotation"
                  : "Generate client summary"
            }}
          </UButton>
        </UForm>
      </UCard>
      <aside class="space-y-4">
        <UCard
          :ui="{ root: 'ring-0 border border-neutral-200 bg-white shadow-lg' }"
          ><p
            class="text-xs font-semibold uppercase tracking-widest text-primary"
          >
            Output logic
          </p>
          <div class="mt-5 space-y-4">
            <div class="flex gap-3">
              <UIcon
                name="i-lucide-1-circle"
                class="mt-0.5 size-5 text-yellow-700"
              />
              <p class="text-sm text-neutral-600">
                <strong class="text-neutral-950">First meeting</strong
                ><br />Creates a structured discovery summary and open
                questions.
              </p>
            </div>
            <div class="flex gap-3">
              <UIcon
                name="i-lucide-2-circle"
                class="mt-0.5 size-5 text-yellow-700"
              />
              <p class="text-sm text-neutral-600">
                <strong class="text-neutral-950">Second meeting</strong
                ><br />Creates a proposal and a draft quotation from both
                conversations.
              </p>
            </div>
          </div></UCard
        >
      </aside>
    </div>
  </main>
  <SummaryPreviewModal
    v-model="summaryModalOpen"
    :summary="generatedSummary"
    @close="summaryModalOpen = false"
    @download="downloadSummary"
    @view="viewSummary"
  />
  <ProposalQuotationModal
    v-model="proposalModalOpen"
    :proposal="generatedProposal"
    :quotation="generatedQuotation"
    @update:proposal="generatedProposal = $event"
    @update:quotation="generatedQuotation = $event"
  />
</template>

<script setup lang="ts">
import * as v from "valibot";
import { downloadSummaryPdf } from "~/utils/downloadSummaryPdf";

const loading = ref(false);

const summaryModalOpen = ref(false);
const generatedSummary = ref(null);

const proposalModalOpen = ref(false);

const generatedProposal = ref(null);
const generatedQuotation = ref(null);

const authStore = useAuthStore();
const toast = useToast();

const meetingTypes = [
  {
    label: "First Meeting(client)",
    value: "discovery_meeting",
  },
  {
    label: "Second Meeting(Team)",
    value: "internal",
  },
];

const {
  data: clientsResponse,
  pending: clientsLoading,
  error,
} = await useLazyFetch("/api/clients");

const resetForm = () => {
  state.clientId = undefined;
  state.meetingType = "";
  state.transcript = "";
};
const clients = computed(() =>
  (clientsResponse.value?.data ?? []).map((client) => ({
    label: `${client.company} (${client.name})`,
    value: client.client_id,
  })),
);

const schema = v.object({
  transcript: v.pipe(
    v.string(),
    v.trim(),
    v.minLength(1, "Transcript is required"),
  ),
  meetingType: v.pipe(v.string(), v.minLength(1, "Meeting type is required")),
  clientId: v.number("Client is required"),
});

type Schema = v.InferOutput<typeof schema>;

const state = reactive({
  transcript: "",
  meetingType: "",
  clientId: undefined as number | undefined,
});

async function onSubmit(event: { data: Schema }) {
  loading.value = true;
  try {
    const response = await $fetch("/api/agent/fathom", {
      method: "POST",
      body: {
        transcript: state.transcript,
        meetingType: state.meetingType,
        clientId: state.clientId,
        userId: authStore.user?.user_id,
      },
    });

    console.log(response);
    if (response.success) {
      if (state.meetingType === "internal") {
        generatedProposal.value = response.proposal;
        generatedQuotation.value = response.quotation;

        proposalModalOpen.value = true;
      } else {
        generatedSummary.value = response.data;
        summaryModalOpen.value = true;
      }

      resetForm();
    }
  } catch (error) {
    console.error("Error processing transcript", error);
    const message =
      error?.data?.message ??
      error?.data?.error ??
      error?.message ??
      "Something went wrong. Please try again.";

    toast.add({
      title: "Generation failed",
      description: message,
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    loading.value = false;
  }
}

const downloadSummary = async () => {
  if (!generatedSummary.value) {
    return;
  }

  try {
    await downloadSummaryPdf(generatedSummary.value);
  } catch (error) {
    console.error("Failed to generate PDF", error);
  }
};

const viewSummary = async () => {
  console.log("View Summary", generatedSummary.value);
};
</script>
