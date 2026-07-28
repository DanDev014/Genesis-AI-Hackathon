<template>
  <div v-if="meeting" class="space-y-6">
    <!-- Meeting -->
    <div>
      <h3 class="text-lg font-semibold text-neutral-950">
        {{ meeting.title }}
      </h3>

      <UBadge color="primary" variant="soft" class="mt-2">
        {{ meeting.meeting_type }}
      </UBadge>
    </div>

    <!-- Client -->
    <div v-if="meeting.key_points?.client">
      <h4 class="mb-2 font-medium text-neutral-950">Client</h4>

      <p class="text-neutral-700">
        {{ meeting.key_points.client.company || "—" }}
      </p>

      <p class="text-sm text-neutral-500">
        {{ meeting.key_points.client.primary_contact || "" }}
      </p>
    </div>

    <!-- Project -->
    <div v-if="meeting.key_points?.project">
      <h4 class="mb-2 font-medium text-neutral-950">Project</h4>

      <p class="font-medium text-neutral-900">
        {{ meeting.key_points.project.name || "—" }}
      </p>

      <p class="text-sm text-neutral-600">
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
      <h4 class="mb-2 font-medium text-neutral-950">Target Audience</h4>

      <ul class="list-disc space-y-1 pl-5 text-neutral-700">
        <li
          v-for="audience in meeting.key_points.target_audience"
          :key="audience.segment"
        >
          <strong class="text-neutral-900">{{ audience.segment }}</strong>
          —
          {{ audience.goal }}
        </li>
      </ul>
    </div>

    <!-- Deliverables -->
    <div v-if="meeting.key_points?.deliverables?.length">
      <h4 class="mb-2 font-medium text-neutral-950">Deliverables</h4>

      <ul class="list-disc space-y-1 pl-5 text-neutral-700">
        <li v-for="item in meeting.key_points.deliverables" :key="item.name">
          {{ item.name }}

          <span v-if="item.duration" class="text-neutral-500"> ({{ item.duration }}) </span>

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
      <h4 class="mb-2 font-medium text-neutral-950">Creative Direction</h4>

      <p v-if="meeting.key_points.creative_direction.description" class="mb-2 text-sm text-neutral-700">
        {{ meeting.key_points.creative_direction.description }}
      </p>

      <ul class="list-disc space-y-1 pl-5 text-neutral-700">
        <li
          v-for="theme in meeting.key_points.creative_direction.messaging_themes ?? []"
          :key="theme"
        >
          {{ theme }}
        </li>
      </ul>
    </div>

    <!-- Timeline -->
    <div v-if="meeting.key_points?.timeline">
      <h4 class="mb-2 font-medium text-neutral-950">Timeline</h4>

      <ul class="space-y-1 text-sm text-neutral-700">
        <li v-if="meeting.key_points.timeline.hackathon_end">
          <strong class="text-neutral-900">Hackathon Ends:</strong>
          {{ meeting.key_points.timeline.hackathon_end }}
        </li>

        <li v-if="meeting.key_points.timeline.summary_video_genesis_quote">
          <strong class="text-neutral-900">Summary Video:</strong>
          {{ meeting.key_points.timeline.summary_video_genesis_quote }}
        </li>

        <li v-if="meeting.key_points.timeline.social_clips_genesis_quote">
          <strong class="text-neutral-900">Social Clips:</strong>
          {{ meeting.key_points.timeline.social_clips_genesis_quote }}
        </li>
      </ul>
    </div>

    <!-- Budget -->
    <div v-if="meeting.key_points?.budget">
      <h4 class="mb-2 font-medium text-neutral-950">Budget</h4>

      <p class="text-neutral-700">
        {{ meeting.key_points.budget.status || "Not yet established." }}
      </p>
    </div>

    <!-- Competition -->
    <div v-if="meeting.key_points?.competition">
      <h4 class="mb-2 font-medium text-neutral-950">Competition</h4>

      <p v-if="meeting.key_points.competition.other_agencies" class="text-neutral-700">
        Other agencies:
        {{ meeting.key_points.competition.other_agencies }}
      </p>

      <p v-if="meeting.key_points.competition.selection_method" class="text-neutral-700">
        Selection:
        {{ meeting.key_points.competition.selection_method }}
      </p>
    </div>

    <!-- Next Steps -->
    <div v-if="meeting.key_points?.next_steps">
      <h4 class="mb-2 font-medium text-neutral-950">Next Steps</h4>

      <div class="grid gap-4 md:grid-cols-2">
        <div v-if="meeting.key_points.next_steps.genesis?.length">
          <h5 class="mb-2 font-medium text-neutral-900">Genesis</h5>

          <ul class="list-disc space-y-1 pl-5 text-neutral-700">
            <li v-for="step in meeting.key_points.next_steps.genesis" :key="step">
              {{ step }}
            </li>
          </ul>
        </div>

        <div v-if="meeting.key_points.next_steps.client?.length">
          <h5 class="mb-2 font-medium text-neutral-900">Client</h5>

          <ul class="list-disc space-y-1 pl-5 text-neutral-700">
            <li v-for="step in meeting.key_points.next_steps.client" :key="step">
              {{ step }}
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Fallback when key_points has none of the structured sections above
         (e.g. a plain transcript that only yielded participants/action
         items, not a full structured extraction) -->
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
        <h4 class="mb-2 font-medium text-neutral-950">Participants</h4>
        <p class="text-sm text-neutral-600">
          {{ meeting.key_points.participants.join(", ") }}
        </p>
      </div>

      <div v-if="meeting.key_points?.action_items?.length">
        <h4 class="mb-2 font-medium text-neutral-950">Action Items</h4>
        <ul class="list-disc space-y-1 pl-5 text-neutral-700">
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
        class="text-sm text-neutral-500"
      >
        No structured details were extracted from this transcript.
      </p>
    </div>
  </div>

  <div v-else class="py-8 text-center text-sm text-neutral-500">
    No summary data available.
  </div>
</template>

<script setup lang="ts">
defineProps<{
  meeting: any | null;
}>();
</script>
