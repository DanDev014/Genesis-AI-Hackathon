<template>
  <UModal v-model:open="open" :dismissible="!saving" :ui="{ content: 'max-w-lg' }">
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
                <UIcon name="i-lucide-user-plus" class="size-5" />
              </span>
              <div>
                <h2 class="text-lg font-semibold text-neutral-950">Add client</h2>
                <p class="text-sm text-neutral-500">
                  Create a new account to start tracking meetings and proposals.
                </p>
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
            <div class="max-h-[60vh] space-y-6 overflow-y-auto px-6 py-6">
              <div class="space-y-4">
                <p class="text-xs font-semibold uppercase tracking-wider text-neutral-400">
                  Contact
                </p>

                <UFormField name="name" label="Contact name" required>
                  <UInput
                    v-model="form.name"
                    icon="i-lucide-user"
                    placeholder="Jane Doe"
                    class="w-full"
                    :ui="{ base: FIELD_BASE }"
                  />
                </UFormField>

                <div class="grid gap-4 sm:grid-cols-2">
                  <UFormField name="email" label="Email" required>
                    <UInput
                      v-model="form.email"
                      icon="i-lucide-mail"
                      type="email"
                      placeholder="jane@company.com"
                      class="w-full"
                      :ui="{ base: FIELD_BASE }"
                    />
                  </UFormField>

                  <UFormField name="phone" label="Phone">
                    <UInput
                      v-model="form.phone"
                      icon="i-lucide-phone"
                      placeholder="Optional"
                      class="w-full"
                      :ui="{ base: FIELD_BASE }"
                    />
                  </UFormField>
                </div>
              </div>

              <div class="space-y-4 border-t border-neutral-100 pt-6">
                <p class="text-xs font-semibold uppercase tracking-wider text-neutral-400">
                  Account
                </p>

                <UFormField name="company" label="Company" required>
                  <UInput
                    v-model="form.company"
                    icon="i-lucide-building-2"
                    placeholder="Acme Ltd"
                    class="w-full"
                    :ui="{ base: FIELD_BASE }"
                  />
                </UFormField>

                <div class="grid gap-4 sm:grid-cols-2">
                  <UFormField name="industry" label="Industry" required>
                    <UInput
                      v-model="form.industry"
                      icon="i-lucide-briefcase"
                      placeholder="e.g. Retail"
                      class="w-full"
                      :ui="{ base: FIELD_BASE }"
                    />
                  </UFormField>

                  <UFormField name="status" label="Status">
                    <USelectMenu
                      v-model="form.status"
                      :items="statuses"
                      class="w-full"
                      :ui="{ base: FIELD_BASE }"
                    />
                  </UFormField>
                </div>
              </div>
            </div>

            <div class="flex justify-end gap-3 border-t border-neutral-100 px-6 py-4">
              <UButton color="neutral" variant="soft" :disabled="saving" @click="open = false">
                Cancel
              </UButton>

              <UButton type="submit" color="primary" :class="isValid ? 'text-white' : ''" :loading="saving" :disabled="!isValid">
                Add client
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

const emit = defineEmits<{
  created: [client: any];
}>();

const authStore = useAuthStore();
const toast = useToast();
const saving = ref(false);

const statuses = ["lead", "Discovery", "Proposal sent", "Active", "Won"];

const schema = v.object({
  name: v.pipe(v.string(), v.minLength(1, "Contact name is required")),
  company: v.pipe(v.string(), v.minLength(1, "Company is required")),
  industry: v.pipe(v.string(), v.minLength(1, "Industry is required")),
  email: v.pipe(v.string(), v.email("Enter a valid email")),
  phone: v.optional(v.string()),
  status: v.optional(v.string()),
});

const form = reactive({
  name: "",
  company: "",
  industry: "",
  email: "",
  phone: "",
  status: "lead",
});

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const isValid = computed(() =>
  form.name.trim().length > 0 &&
  form.company.trim().length > 0 &&
  form.industry.trim().length > 0 &&
  EMAIL_RE.test(form.email.trim()),
);

function resetForm() {
  form.name = "";
  form.company = "";
  form.industry = "";
  form.email = "";
  form.phone = "";
  form.status = "lead";
}

async function save() {
  if (!isValid.value) return;

  saving.value = true;
  try {
    const response = await $fetch<{ success: boolean; data: any }>("/api/clients", {
      method: "POST",
      body: {
        user_id: authStore.user?.user_id,
        name: form.name,
        company: form.company,
        industry: form.industry,
        email: form.email,
        phone: form.phone || undefined,
        status: form.status,
      },
    });

    emit("created", response.data);
    open.value = false;
    resetForm();

    toast.add({
      title: "Client added",
      color: "success",
      icon: "i-lucide-circle-check",
    });
  } catch (error: any) {
    toast.add({
      title: "Couldn't add client",
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
