<script setup lang="ts">
const open = defineModel<boolean>();

defineProps<{
  summary: any;
}>();

const emit = defineEmits<{
  close: [];
  view: [];
  download: [];
}>();
</script>

<template>
  <UModal v-model:open="open" :dismissible="false" :ui="{ root: 'bg-white ' }">
    <template #content>
      <div class="p-6 space-y-6">
        <div class="text-center">
          <UIcon
            name="i-lucide-circle-check-big"
            class="size-14 text-success mx-auto mb-3"
          />

          <h2 class="text-2xl font-semibold">Summary Generated</h2>

          <p class="text-sm text-muted mt-1">
            Review the generated meeting summary before proceeding.
          </p>
        </div>

        <UDivider />

        <div v-if="summary" class="space-y-6 max-h-[60vh] overflow-y-auto pr-1">
          <div>
            <h3 class="font-semibold text-lg">
              {{ summary.title }}
            </h3>

            <UBadge color="primary" variant="soft" class="mt-2">
              {{ summary.meeting_type }}
            </UBadge>
          </div>

          <div>
            <h4 class="font-medium mb-2">Client</h4>

            <p>
              {{ summary.key_points.client.company }}
            </p>

            <p class="text-sm text-muted">
              {{ summary.key_points.client.primary_contact }}
            </p>
          </div>

          <div>
            <h4 class="font-medium mb-2">Project</h4>

            <p>{{ summary.key_points.project.name }}</p>

            <p class="text-sm text-muted">
              {{ summary.key_points.project.objective }}
            </p>
          </div>

          <div>
            <h4 class="font-medium mb-2">Deliverables</h4>

            <ul class="list-disc ml-5 space-y-1">
              <li
                v-for="item in summary.key_points.deliverables"
                :key="item.name"
              >
                {{ item.name }}
                <span v-if="item.duration"> ({{ item.duration }}) </span>
              </li>
            </ul>
          </div>

          <div>
            <h4 class="font-medium mb-2">Timeline</h4>

            <ul class="space-y-1 text-sm">
              <li>
                <strong>Hackathon Ends:</strong>
                {{ summary.key_points.timeline.hackathon_end }}
              </li>

              <li>
                <strong>Summary Video:</strong>
                {{ summary.key_points.timeline.summary_video_quote }}
              </li>

              <li>
                <strong>Social Clips:</strong>
                {{ summary.key_points.timeline.social_clips_quote }}
              </li>
            </ul>
          </div>

          <div>
            <h4 class="font-medium mb-2">Next Steps</h4>

            <div class="grid md:grid-cols-2 gap-4">
              <div>
                <h5 class="font-medium mb-2">Genesis</h5>

                <ul class="list-disc ml-5 space-y-1">
                  <li
                    v-for="step in summary.key_points.next_steps.genesis"
                    :key="step"
                  >
                    {{ step }}
                  </li>
                </ul>
              </div>

              <div>
                <h5 class="font-medium mb-2">Client</h5>

                <ul class="list-disc ml-5 space-y-1">
                  <li
                    v-for="step in summary.key_points.next_steps.client"
                    :key="step"
                  >
                    {{ step }}
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <UDivider />

        <div class="flex justify-end gap-3">
          <UButton color="neutral" variant="soft" @click="emit('close')">
            Close
          </UButton>

          <UButton
            icon="i-lucide-download"
            color="neutral"
            @click="emit('download')"
          >
            Download PDF
          </UButton>

          <UButton trailing-icon="i-lucide-arrow-right" @click="emit('view')">
            View Summary
          </UButton>
        </div>
      </div>
    </template>
  </UModal>
</template>
