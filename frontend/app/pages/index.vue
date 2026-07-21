<template>
  <div class="min-h-screen flex items-center justify-center px-4">
    <UCard :ui="{ root: 'ring-0 bg-black shadow-2xl w-full max-w-sm' }">
      <div class="text-center mb-6">
        <h1 class="text-2xl font-bold text-white">Welcome back</h1>
        <p class="text-neutral-400 text-sm mt-1">Sign in to your account</p>
      </div>

      <UForm
        :schema="loginSchema"
        :state="state"
        class="space-y-4"
        @submit="onSubmit"
      >
        <UFormField label="Email" name="email" :ui="{ label: 'text-white' }">
          <UInput
            v-model="state.email"
            type="email"
            placeholder="you@company.com"
            class="w-full"
            :ui="{
              base: 'bg-white text-neutral-900 ring-1 ring-neutral-300 focus:ring-2 focus:ring-yellow-500 focus-visible:ring-2 focus-visible:ring-yellow-500',
            }"
          />
        </UFormField>

        <UFormField
          label="Password"
          name="password"
          :ui="{ label: 'text-white' }"
        >
          <UInput
            v-model="state.password"
            :type="showPassword ? 'text' : 'password'"
            placeholder="••••••••"
            class="w-full"
            :ui="{
              base: 'bg-white text-neutral-900 ring-1 ring-neutral-300 focus:ring-2 focus:ring-yellow-500 focus-visible:ring-2 focus-visible:ring-yellow-500',
            }"
          >
            <template #trailing>
              <UButton
                color="neutral"
                variant="link"
                size="sm"
                :icon="showPassword ? 'i-lucide-eye-off' : 'i-lucide-eye'"
                :padded="false"
                @click="showPassword = !showPassword"
              />
            </template>
          </UInput>
        </UFormField>

        <UButton
          type="submit"
          block
          :loading="authStore.loading"
          class="bg-yellow-500 hover:bg-yellow-400 text-black font-semibold justify-center"
        >
          {{ authStore.loading ? "Signing in..." : "Sign In" }}
        </UButton>
      </UForm>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import * as v from "valibot";

definePageMeta({ layout: false });

const loginSchema = v.object({
  email: v.pipe(
    v.string(),
    v.nonEmpty("Email is required"),
    v.email("Enter a valid email address"),
  ),
  password: v.pipe(v.string(), v.nonEmpty("Password is required")),
});

const toast = useToast();
const authStore = useAuthStore();

const state = reactive({
  email: "",
  password: "",
});

const showPassword = ref(false);

async function onSubmit() {
  try {
    await authStore.login(state.email, state.password);

    toast.add({
      title: "Login successful",
      description: "Redirecting to your dashboard...",
      color: "success",
      icon: "i-lucide-check-circle",
    });

    await navigateTo("/dashboard");
  } catch (err: any) {
    toast.add({
      title: "Login failed",
      description: err?.data?.statusMessage || "Invalid email or password.",
      color: "error",
      icon: "i-lucide-alert-circle",
    });
  }
}
</script>
