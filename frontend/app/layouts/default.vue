<template>
  <UDashboardGroup>
    <UDashboardSidebar class="bg-black text-white border-r border-neutral-800">
      <!-- Logo -->
      <UDashboardSidebarHeader>
        <div>Logo</div>
      </UDashboardSidebarHeader>

      <!-- Navigation -->
      <UDashboardSidebarContent class="px-3 py-4">
        <UNavigationMenu
          orientation="vertical"
          :items="links"
          :ui="{
            link: 'rounded-lg px-3 py-2 transition-colors',
            linkActive: 'bg-yellow-400 text-black font-semibold',
            linkInactive: 'text-gray-300 hover:bg-yellow-400 hover:text-black',
          }"
        />
      </UDashboardSidebarContent>

      <!-- Footer -->
      <UDashboardSidebarFooter
        class="border-t border-neutral-800 p-4 absolute bottom-0"
      >
        <div class="flex items-center gap-3">
          <UAvatar src="https://i.pravatar.cc/100" alt="User" size="lg" />

          <div class="flex flex-col">
            <span class="font-semibold text-white"> John Doe </span>
            <span class="text-sm text-gray-400"> Administrator </span>
          </div>
        </div>
      </UDashboardSidebarFooter>
    </UDashboardSidebar>

    <div class="flex min-h-screen flex-1 flex-col bg-white w-[100%]">
      <UDashboardNavbar class="w-[100%]" :ui="{ root: 'border-b-0' }">
        <template #right>
          <UButton
            label="Logout"
            class="text-white"
            @click="onLoginClick"
            :loading="loading"
          />
        </template>
      </UDashboardNavbar>

      <UDashboardPanel>
        <UDashboardPanelContent>
          <div class="w-full min-h-screen bg-white text-black">
            <slot />
          </div>
        </UDashboardPanelContent>
      </UDashboardPanel>
    </div>
  </UDashboardGroup>
</template>

<script setup lang="ts">
const authStore = useAuthStore();
const loading = ref(false);
const toast = useToast();

const links = [
  {
    label: "Dashboard",
    icon: "i-lucide-layout-dashboard",
    to: "/dashboard",
  },
  {
    label: "Clients",
    icon: "i-lucide-users",
    to: "/clients",
  },
  {
    label: "Proposals",
    icon: "i-lucide-file-text",
    to: "/proposals",
  },
];

const onLoginClick = async () => {
  loading.value = true;

  try {
    await authStore.logout();
    toast.add({
      title: "Logout successful",
      description: "Redirecting to login page",
      color: "success",
      icon: "i-lucide-check-circle",
    });
  } catch (error) {
    console.error("Error logging out", error);
  } finally {
    loading.value = false;
  }
};
</script>
