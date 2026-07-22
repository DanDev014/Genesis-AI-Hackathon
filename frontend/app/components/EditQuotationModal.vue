<template>
  <UModal v-model:open="open" :dismissible="!saving" :ui="{ content: 'max-w-3xl' }">
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
            <h2 class="text-lg font-semibold text-neutral-950">Edit quotation</h2>
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
            <div class="space-y-3">
              <div
                v-for="(line, i) in form.line_items"
                :key="i"
                class="grid grid-cols-12 gap-2"
              >
                <UInput
                  v-model="line.item"
                  class="col-span-6"
                  placeholder="Item"
                  :ui="{ base: FIELD_BASE }"
                />
                <UInput
                  v-model.number="line.qty"
                  type="number"
                  class="col-span-2"
                  placeholder="Qty"
                  :ui="{ base: FIELD_BASE }"
                />
                <UInput
                  v-model.number="line.unit_price"
                  type="number"
                  class="col-span-3"
                  placeholder="Unit price"
                  :ui="{ base: FIELD_BASE }"
                />
                <UButton
                  icon="i-lucide-trash-2"
                  color="error"
                  variant="ghost"
                  class="col-span-1"
                  @click="form.line_items.splice(i, 1)"
                />
              </div>

              <UButton
                icon="i-lucide-plus"
                color="neutral"
                variant="outline"
                size="xs"
                @click="form.line_items.push({ item: '', qty: 1, unit_price: 0 })"
              >
                Add line item
              </UButton>
            </div>

            <div class="grid gap-4 sm:grid-cols-3">
              <UFormField name="tax_rate" label="Tax rate (%)">
                <UInput
                  v-model.number="form.tax_rate"
                  type="number"
                  class="w-full"
                  :ui="{ base: FIELD_BASE }"
                />
              </UFormField>

              <UFormField name="discount_amount" label="Discount">
                <UInput
                  v-model.number="form.discount_amount"
                  type="number"
                  class="w-full"
                  :ui="{ base: FIELD_BASE }"
                />
              </UFormField>

              <UFormField name="currency" label="Currency">
                <UInput v-model="form.currency" class="w-full" :ui="{ base: FIELD_BASE }" />
              </UFormField>
            </div>

            <UFormField name="status" label="Status" required>
              <USelectMenu
                v-model="form.status"
                :items="statuses"
                class="w-full"
                :ui="{ base: FIELD_BASE }"
              />
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

const FIELD_BASE =
  "bg-white text-neutral-900 ring-neutral-200 focus:ring-2 focus:ring-[#e0b818]";

const open = defineModel<boolean>({ default: false });

const props = defineProps<{
  quotation: any;
}>();

const emit = defineEmits<{
  saved: [quotation: any];
}>();

const toast = useToast();
const saving = ref(false);

const statuses = ["draft", "sent", "accepted", "expired"];

const schema = v.object({
  status: v.pipe(v.string(), v.minLength(1, "Status is required")),
  currency: v.pipe(v.string(), v.minLength(1, "Currency is required")),
  tax_rate: v.number(),
  discount_amount: v.number(),
});

const form = reactive({
  line_items: [] as { item: string; qty: number; unit_price: number }[],
  tax_rate: 16,
  discount_amount: 0,
  currency: "KES",
  status: "draft",
});

watch(
  () => props.quotation,
  (quotation) => {
    form.line_items = (quotation?.line_items ?? []).map((it: any) => ({
      item: it.item ?? "",
      qty: it.qty ?? 1,
      unit_price: it.unit_price ?? 0,
    }));
    form.tax_rate = quotation?.tax_rate ?? 16;
    form.discount_amount = quotation?.discount_amount ?? 0;
    form.currency = quotation?.currency ?? "KES";
    form.status = quotation?.status ?? "draft";
  },
  { immediate: true },
);

async function save() {
  if (!props.quotation?.quote_id) return;

  saving.value = true;
  try {
    const response = await $fetch<{ success: boolean; data: Record<string, any> }>(
      `/api/quotes/${props.quotation.quote_id}`,
      {
        method: "PATCH",
        body: {
          line_items: form.line_items.filter((li) => li.item.trim()),
          tax_rate: form.tax_rate,
          discount_amount: form.discount_amount,
          currency: form.currency,
          status: form.status,
        },
      },
    );

    emit("saved", response.data);
    open.value = false;

    toast.add({
      title: "Quotation updated",
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
