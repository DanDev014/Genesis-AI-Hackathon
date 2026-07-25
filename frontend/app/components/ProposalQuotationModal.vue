<template>
  <UModal
    v-model:open="open"
    :dismissible="quotationEdited"
    :ui="{ content: 'max-w-6xl' }"
  >
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
            <div>
              <h2 class="text-lg font-semibold text-neutral-950">
                Proposal & Quotation
              </h2>
              <p class="text-sm text-neutral-500">
                Review the generated proposal and quotation.
              </p>
            </div>

            <UButton
              color="neutral"
              variant="ghost"
              icon="i-lucide-x"
              @click="attemptClose"
            />
          </div>
        </template>

        <UTabs :items="tabs" class="w-full bg-white">
          <template #proposal>
            <div class="h-[75vh] overflow-y-auto bg-white p-6">
              <div v-if="proposal" class="space-y-6">
                <div class="flex flex-wrap items-center justify-between gap-3">
                  <div class="flex items-center gap-2">
                    <UBadge color="primary" variant="soft">
                      {{ proposal.status }}
                    </UBadge>
                    <span class="text-sm text-neutral-500"
                      >v{{ proposal.version }}</span
                    >
                  </div>

                  <div class="flex gap-2">
                    <UButton
                      icon="i-lucide-download"
                      color="neutral"
                      variant="outline"
                      :loading="downloadingProposal"
                      :disabled="downloadingProposal"
                      @click="downloadProposal"
                    >
                      Download PDF
                    </UButton>

                    <UButton
                      icon="i-lucide-send"
                      class="bg-primary font-semibold text-black hover:bg-yellow-400"
                      @click="sendProposalOpen = true"
                    >
                      Send to client
                    </UButton>

                    <UButton
                      icon="i-lucide-pencil"
                      color="primary"
                      variant="soft"
                      @click="editProposalOpen = true"
                    >
                      Edit
                    </UButton>
                  </div>
                </div>

                <div>
                  <h3 class="mb-1 text-sm font-semibold text-neutral-950">
                    Client
                  </h3>
                  <p class="text-sm text-neutral-700">
                    {{ proposal.client?.company || "—" }}
                  </p>
                  <p class="text-sm text-neutral-500">
                    {{ proposal.client?.name || "" }}
                  </p>
                </div>

                <div>
                  <h3 class="mb-1 text-sm font-semibold text-neutral-950">
                    Scope of work
                  </h3>
                  <p class="whitespace-pre-line text-sm text-neutral-700">
                    {{ proposal.scope_of_work || "Not yet established." }}
                  </p>
                </div>

                <div>
                  <h3 class="mb-1 text-sm font-semibold text-neutral-950">
                    Deliverables
                  </h3>
                  <ul class="list-disc space-y-1 pl-5">
                    <li
                      v-for="(item, i) in proposal.deliverables"
                      :key="i"
                      class="text-sm text-neutral-700"
                    >
                      {{ item }}
                    </li>
                  </ul>
                </div>

                <div>
                  <h3 class="mb-1 text-sm font-semibold text-neutral-950">
                    Timeline
                  </h3>
                  <p class="text-sm text-neutral-700">
                    {{ proposal.timeline || "Not yet established." }}
                  </p>
                </div>

                <div v-if="proposal.proposal_html">
                  <h3 class="mb-2 text-sm font-semibold text-neutral-950">
                    Branded preview
                  </h3>
                  <iframe
                    :srcdoc="proposal.proposal_html"
                    class="h-[50vh] w-full rounded-md border border-neutral-200"
                  />
                </div>
              </div>

              <div
                v-else
                class="flex h-full items-center justify-center text-sm text-neutral-500"
              >
                No proposal available.
              </div>
            </div>
          </template>

          <template #quotation>
            <div class="h-[75vh] overflow-y-auto bg-white p-6">
              <div v-if="quotation" class="space-y-6">
                <div class="flex flex-wrap items-center justify-between gap-3">
                  <div class="flex items-center gap-2">
                    <UBadge color="primary" variant="soft">
                      {{ quotation.status }}
                    </UBadge>
                    <UBadge v-if="!quotationEdited" color="warning" variant="subtle">
                      Needs pricing review
                    </UBadge>
                  </div>

                  <div class="flex gap-2">
                    <UButton
                      v-if="quotationEdited"
                      icon="i-lucide-download"
                      color="neutral"
                      variant="outline"
                      :loading="downloadingQuotation"
                      :disabled="downloadingQuotation"
                      @click="downloadQuotation"
                    >
                      Download PDF
                    </UButton>

                    <UButton
                      icon="i-lucide-pencil"
                      color="primary"
                      variant="soft"
                      @click="editQuotationOpen = true"
                    >
                      Edit
                    </UButton>
                  </div>
                </div>

                <p v-if="!quotationEdited" class="text-sm text-neutral-500">
                  This quotation was auto-drafted with placeholder pricing.
                  Edit it with real numbers before downloading or closing.
                </p>

                <div class="overflow-x-auto">
                  <table class="min-w-full border-collapse">
                    <thead>
                      <tr class="border-b border-neutral-200 text-left">
                        <th class="py-3 text-neutral-950">Item</th>
                        <th class="py-3 text-right text-neutral-950">Qty</th>
                        <th class="py-3 text-right text-neutral-950">
                          Unit Price
                        </th>
                        <th class="py-3 text-right text-neutral-950">
                          Amount
                        </th>
                      </tr>
                    </thead>

                    <tbody>
                      <tr
                        v-for="(item, index) in quotation.line_items"
                        :key="index"
                        class="border-b border-neutral-100"
                      >
                        <td class="py-3">
                          <div class="font-medium text-neutral-900">
                            {{ item.item }}
                          </div>
                          <div
                            v-if="item.description"
                            class="text-sm text-neutral-500"
                          >
                            {{ item.description }}
                          </div>
                        </td>
                        <td class="py-3 text-right text-neutral-700">
                          {{ item.qty }}
                        </td>
                        <td class="py-3 text-right text-neutral-700">
                          {{ item.unit_price }}
                        </td>
                        <td class="py-3 text-right text-neutral-700">
                          {{ item.amount }}
                        </td>
                      </tr>
                    </tbody>
                  </table>

                  <div class="mt-6 flex justify-end">
                    <div class="w-72 space-y-2">
                      <div class="flex justify-between text-neutral-700">
                        <span>Subtotal</span>
                        <span>{{ quotation.subtotal }}</span>
                      </div>

                      <div
                        class="flex justify-between text-lg font-semibold text-neutral-950"
                      >
                        <span>Total</span>
                        <span>{{ quotation.total ?? quotation.total_amount }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div
                v-else
                class="flex h-80 items-center justify-center text-sm text-neutral-500"
              >
                No quotation available.
              </div>
            </div>
          </template>
        </UTabs>

        <template #footer>
          <div class="flex items-center justify-between">
            <p v-if="!quotationEdited" class="text-xs text-neutral-500">
              Edit the quotation's pricing to enable closing.
            </p>
            <span v-else />

            <UButton color="neutral" variant="soft" @click="attemptClose">
              Close
            </UButton>
          </div>
        </template>
      </UCard>
    </template>
  </UModal>

  <EditProposalModal v-model="editProposalOpen" :proposal="proposal" @saved="onProposalSaved" />
  <EditQuotationModal v-model="editQuotationOpen" :quotation="quotation" @saved="onQuotationSaved" />
  <SendProposalModal v-model="sendProposalOpen" :proposal="proposal" @sent="onProposalSaved" />
</template>

<script setup lang="ts">
import { downloadProposalPdf } from "~/utils/downloadProposalPdf";
import { downloadQuotationPdf } from "~/utils/downloadQuotationPdf";

const open = defineModel<boolean>({ default: false });

const props = defineProps<{
  proposal: any | null;
  quotation: any | null;
}>();

const emit = defineEmits<{
  "update:proposal": [proposal: any];
  "update:quotation": [quotation: any];
}>();

const toast = useToast();

const tabs = [
  { label: "Proposal", slot: "proposal" },
  { label: "Quotation", slot: "quotation" },
];

const editProposalOpen = ref(false);
const editQuotationOpen = ref(false);
const sendProposalOpen = ref(false);

// A freshly generated quotation always starts un-priced (line items seeded
// at unit_price: 0 — see genesis_agent's _quote_line_items_from_key_points).
// The user must review/edit it with real pricing before the modal can be
// closed or a PDF downloaded — resets whenever a new quotation comes in.
const quotationEdited = ref(false);

watch(
  () => props.quotation?.quote_id,
  () => {
    quotationEdited.value = false;
  },
);

function onProposalSaved(updated: any) {
  emit("update:proposal", updated);
}

function onQuotationSaved(updated: any) {
  emit("update:quotation", updated);
  quotationEdited.value = true;
}

function attemptClose() {
  if (!quotationEdited.value) {
    toast.add({
      title: "Review the quotation first",
      description: "Edit the quotation with real pricing before closing this window.",
      color: "warning",
      icon: "i-lucide-triangle-alert",
    });
    return;
  }
  open.value = false;
}

const downloadingProposal = ref(false);
const downloadingQuotation = ref(false);

async function downloadProposal() {
  if (!props.proposal || downloadingProposal.value) return;

  downloadingProposal.value = true;
  try {
    await downloadProposalPdf(props.proposal);
  } catch (error: any) {
    console.error("Failed to generate proposal PDF", error);
    toast.add({
      title: "Couldn't download the PDF",
      description: error?.message ?? "Something went wrong while generating the file.",
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    downloadingProposal.value = false;
  }
}

async function downloadQuotation() {
  if (!props.quotation || downloadingQuotation.value) return;

  downloadingQuotation.value = true;
  try {
    await downloadQuotationPdf(props.quotation);
  } catch (error: any) {
    console.error("Failed to generate quotation PDF", error);
    toast.add({
      title: "Couldn't download the PDF",
      description: error?.message ?? "Something went wrong while generating the file.",
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    downloadingQuotation.value = false;
  }
}
</script>
