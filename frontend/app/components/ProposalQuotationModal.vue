<template>
  <UModal v-model:open="open" :ui="{ content: 'max-w-6xl' }">
    <template #content>
      <UCard
        :ui="{
          root: 'border-0 shadow-none',
          body: 'p-0',
          header: 'px-6 py-4 border-b',
          footer: 'px-6 py-4 border-t',
        }"
      >
        <template #header>
          <div class="flex items-center justify-between">
            <div>
              <h2 class="text-lg font-semibold text-white">
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
              @click="open = false"
            />
          </div>
        </template>

        <UTabs :items="tabs" class="w-full">
          <template #proposal>
            <div class="h-[75vh]">
              <iframe
                v-if="proposal?.proposal_html"
                :srcdoc="proposal.proposal_html"
                class="h-full w-full rounded-md border border-neutral-200"
              />

              <div
                v-else
                class="flex h-full items-center justify-center text-sm text-neutral-500"
              >
                No proposal available.
              </div>
            </div>
          </template>

          <template #quotation>
            <div class="p-6">
              <div v-if="quotation" class="overflow-x-auto">
                <table class="min-w-full border-collapse">
                  <thead>
                    <tr class="border-b border-neutral-200 text-left">
                      <th class="py-3">Item</th>
                      <th class="py-3 text-right">Qty</th>
                      <th class="py-3 text-right">Unit Price</th>
                      <th class="py-3 text-right">Amount</th>
                    </tr>
                  </thead>

                  <tbody>
                    <tr
                      v-for="(item, index) in quotation.line_items"
                      :key="index"
                      class="border-b border-neutral-100"
                    >
                      <td class="py-3">
                        <div class="font-medium">
                          {{ item.item }}
                        </div>

                        <div
                          v-if="item.description"
                          class="text-sm text-neutral-500"
                        >
                          {{ item.description }}
                        </div>
                      </td>

                      <td class="py-3 text-right">
                        {{ item.qty }}
                      </td>

                      <td class="py-3 text-right">
                        {{ item.unit_price }}
                      </td>

                      <td class="py-3 text-right">
                        {{ item.amount }}
                      </td>
                    </tr>
                  </tbody>
                </table>

                <div class="mt-6 flex justify-end">
                  <div class="w-72 space-y-2">
                    <div class="flex justify-between">
                      <span>Subtotal</span>
                      <span>{{ quotation.subtotal }}</span>
                    </div>

                    <div class="flex justify-between font-semibold text-lg">
                      <span>Total</span>
                      <span>{{ quotation.total }}</span>
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
          <div class="flex justify-end">
            <UButton color="neutral" variant="soft" @click="open = false">
              Close
            </UButton>
          </div>
        </template>
      </UCard>
    </template>
  </UModal>
</template>

<script setup lang="ts">
const open = defineModel<boolean>({
  default: false,
});

defineProps<{
  proposal: any | null;
  quotation: any | null;
}>();

const tabs = [
  {
    label: "Proposal",
    slot: "proposal",
  },
  {
    label: "Quotation",
    slot: "quotation",
  },
];
</script>
