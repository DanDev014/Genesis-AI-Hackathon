<script setup lang="ts">
import { computed } from "vue";

const open = defineModel<boolean>();

const props = defineProps<{
  summary: any;
}>();

const emit = defineEmits<{
  close: [];
  view: [];
  download: [];
}>();

const meeting = computed(
  () => props.summary?.first_meeting_deliverables ?? null,
);
</script>

<template>
  <UModal v-model:open="open" :dismissible="false">
    <template #content>
      <div class="flex max-h-[85vh] flex-col p-6">
        <div class="shrink-0 text-center">
          <UIcon
            name="i-lucide-circle-check-big"
            class="mx-auto mb-3 size-14 text-success"
          />

          <h2 class="text-2xl font-semibold">Summary Generated Successfully</h2>

          <p class="mt-1 text-sm text-muted">
            Review the generated meeting summary before proceeding.
          </p>
        </div>

        <UDivider class="my-6 shrink-0" />

        <div
          v-if="meeting"
          class="min-h-0 flex-1 space-y-6 overflow-y-auto pr-1"
        >
          <!-- Meeting -->
          <div>
            <h3 class="text-lg font-semibold">
              {{ meeting.title }}
            </h3>

            <UBadge color="primary" variant="soft" class="mt-2">
              {{ meeting.meeting_type }}
            </UBadge>
          </div>

          <!-- Client -->
          <div v-if="meeting.key_points?.client">
            <h4 class="mb-2 font-medium">Client</h4>

            <p>
              {{ meeting.key_points.client.company || "—" }}
            </p>

            <p class="text-sm text-muted">
              {{ meeting.key_points.client.primary_contact || "" }}
            </p>
          </div>

          <!-- Project -->
          <div v-if="meeting.key_points?.project">
            <h4 class="mb-2 font-medium">Project</h4>

            <p class="font-medium">
              {{ meeting.key_points.project.name || "—" }}
            </p>

            <p class="text-sm text-muted">
              {{ meeting.key_points.project.objective || "" }}
            </p>

            <UBadge
              v-if="meeting.key_points.project.type"
              color="neutral"
              variant="soft"
              class="mt-2"
            >
              {{ meeting.key_points.project.type }}
            </UBadge>
          </div>

          <!-- Target Audience -->
          <div v-if="meeting.key_points?.target_audience?.length">
            <h4 class="mb-2 font-medium">Target Audience</h4>

            <ul class="list-disc space-y-1 pl-5">
              <li
                v-for="audience in meeting.key_points.target_audience"
                :key="audience.segment"
              >
                <strong>{{ audience.segment }}</strong>
                —
                {{ audience.goal }}
              </li>
            </ul>
          </div>

          <!-- Deliverables -->
          <div v-if="meeting.key_points?.deliverables?.length">
            <h4 class="mb-2 font-medium">Deliverables</h4>

            <ul class="list-disc space-y-1 pl-5">
              <li
                v-for="item in meeting.key_points.deliverables"
                :key="item.name"
              >
                {{ item.name }}

                <span v-if="item.duration"> ({{ item.duration }}) </span>

                <UBadge
                  v-if="item.status"
                  color="success"
                  variant="soft"
                  size="xs"
                  class="ml-2"
                >
                  {{ item.status }}
                </UBadge>
              </li>
            </ul>
          </div>

          <!-- Creative Direction -->
          <div v-if="meeting.key_points?.creative_direction">
            <h4 class="mb-2 font-medium">Creative Direction</h4>

            <p v-if="meeting.key_points.creative_direction.description" class="mb-2 text-sm">
              {{ meeting.key_points.creative_direction.description }}
            </p>

            <ul class="list-disc space-y-1 pl-5">
              <li
                v-for="theme in meeting.key_points.creative_direction
                  .messaging_themes ?? []"
                :key="theme"
              >
                {{ theme }}
              </li>
            </ul>
          </div>

          <!-- Timeline -->
          <div v-if="meeting.key_points?.timeline">
            <h4 class="mb-2 font-medium">Timeline</h4>

            <ul class="space-y-1 text-sm">
              <li v-if="meeting.key_points.timeline.hackathon_end">
                <strong>Hackathon Ends:</strong>
                {{ meeting.key_points.timeline.hackathon_end }}
              </li>

              <li v-if="meeting.key_points.timeline.summary_video_genesis_quote">
                <strong>Summary Video:</strong>
                {{ meeting.key_points.timeline.summary_video_genesis_quote }}
              </li>

              <li v-if="meeting.key_points.timeline.social_clips_genesis_quote">
                <strong>Social Clips:</strong>
                {{ meeting.key_points.timeline.social_clips_genesis_quote }}
              </li>
            </ul>
          </div>

          <!-- Budget -->
          <div v-if="meeting.key_points?.budget">
            <h4 class="mb-2 font-medium">Budget</h4>

            <p>
              {{ meeting.key_points.budget.status || "Not yet established." }}
            </p>
          </div>

          <!-- Competition -->
          <div v-if="meeting.key_points?.competition">
            <h4 class="mb-2 font-medium">Competition</h4>

            <p v-if="meeting.key_points.competition.other_agencies">
              Other agencies:
              {{ meeting.key_points.competition.other_agencies }}
            </p>

            <p v-if="meeting.key_points.competition.selection_method">
              Selection:
              {{ meeting.key_points.competition.selection_method }}
            </p>
          </div>

          <!-- Next Steps -->
          <div v-if="meeting.key_points?.next_steps">
            <h4 class="mb-2 font-medium">Next Steps</h4>

            <div class="grid gap-4 md:grid-cols-2">
              <div v-if="meeting.key_points.next_steps.genesis?.length">
                <h5 class="mb-2 font-medium">Genesis</h5>

                <ul class="list-disc space-y-1 pl-5">
                  <li
                    v-for="step in meeting.key_points.next_steps.genesis"
                    :key="step"
                  >
                    {{ step }}
                  </li>
                </ul>
              </div>

              <div v-if="meeting.key_points.next_steps.client?.length">
                <h5 class="mb-2 font-medium">Client</h5>

                <ul class="list-disc space-y-1 pl-5">
                  <li
                    v-for="step in meeting.key_points.next_steps.client"
                    :key="step"
                  >
                    {{ step }}
                  </li>
                </ul>
              </div>
            </div>
          </div>

          <!-- Fallback when key_points has none of the structured sections
               above (e.g. a plain transcript that only yielded
               participants/action_items, not a full structured extraction) -->
          <div
            v-if="
              !meeting.key_points?.client &&
              !meeting.key_points?.project &&
              !meeting.key_points?.deliverables?.length &&
              !meeting.key_points?.timeline &&
              !meeting.key_points?.budget &&
              !meeting.key_points?.next_steps
            "
            class="space-y-4"
          >
            <div v-if="meeting.key_points?.participants?.length">
              <h4 class="mb-2 font-medium">Participants</h4>
              <p class="text-sm text-muted">
                {{ meeting.key_points.participants.join(", ") }}
              </p>
            </div>

            <div v-if="meeting.key_points?.action_items?.length">
              <h4 class="mb-2 font-medium">Action Items</h4>
              <ul class="list-disc space-y-1 pl-5">
                <li v-for="item in meeting.key_points.action_items" :key="item">
                  {{ item }}
                </li>
              </ul>
            </div>

            <p
              v-if="
                !meeting.key_points?.participants?.length &&
                !meeting.key_points?.action_items?.length
              "
              class="text-sm text-muted"
            >
              No structured details were extracted from this transcript.
            </p>
          </div>
        </div>

        <div v-else class="min-h-0 flex-1 py-8 text-center text-sm text-muted">
          No summary data available.
        </div>

        <UDivider class="my-6 shrink-0" />

        <div class="flex shrink-0 justify-end gap-3">
          <UButton
            color="neutral"
            variant="soft"
            @click="
              open = false;
              emit('close');
            "
          >
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
