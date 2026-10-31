<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: {
    type: String,
    required: true
  },
  size: {
    type: [Number, String],
    default: 20
  }
})

// 统一 24 网格、1.8 描边、圆角端点；所有图形只用 path，保证笔画一致。
const paths = {
  menu: [
    'M4 7h16',
    'M4 12h16',
    'M4 17h16'
  ],
  home: [
    'M3.5 10.8 12 3.6l8.5 7.2',
    'M5.6 9.3V20a.8.8 0 0 0 .8.8h11.2a.8.8 0 0 0 .8-.8V9.3',
    'M9.6 20.8v-5.9h4.8v5.9'
  ],
  compass: [
    'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z',
    'm15.4 8.6-2.1 4.7-4.7 2.1 2.1-4.7 4.7-2.1Z'
  ],
  bookmark: [
    'm19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16Z'
  ],
  bell: [
    'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9',
    'M10.3 21a2 2 0 0 0 3.4 0'
  ],
  user: [
    'M20 21a8 8 0 0 0-16 0',
    'M12 13a5 5 0 1 0 0-10 5 5 0 0 0 0 10Z'
  ],
  edit: [
    'M12 20h9',
    'M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5Z'
  ],
  search: [
    'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z',
    'm21 21-4.3-4.3'
  ],
  arrow: [
    'M4 12h16',
    'm14 6 6 6-6 6'
  ],
  like: [
    'M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.51 4.04 3 5.5l7 7 7-7Z'
  ],
  chat: [
    'M7.9 20A9 9 0 1 0 4 16.1L2 22l5.9-2Z'
  ],
  eye: [
    'M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z',
    'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z'
  ],
  close: [
    'M6 6l12 12',
    'M18 6 6 18'
  ],
  logout: [
    'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4',
    'm16 17 5-5-5-5',
    'M21 12H9'
  ],
  grid: [
    'M4 4h6v6H4V4Z',
    'M14 4h6v6h-6V4Z',
    'M4 14h6v6H4v-6Z',
    'M14 14h6v6h-6v-6Z'
  ],
  upload: [
    'M12 16V4',
    'm7 9 5-5 5 5',
    'M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2'
  ],
  check: [
    'm5 12 4.5 4.5L19 7'
  ],
  help: [
    'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z',
    'M9.1 9a3 3 0 0 1 5.8 1c0 2-3 2.2-3 4',
    'M12 17.5h.01'
  ],
  back: [
    'M20 12H4',
    'm10 18-6-6 6-6'
  ],
  refresh: [
    'M21 12a9 9 0 0 0-15.4-6.4L3 8',
    'M3 3v5h5',
    'M3 12a9 9 0 0 0 15.4 6.4L21 16',
    'M16 16h5v5'
  ],
  plus: [
    'M12 5v14',
    'M5 12h14'
  ],
  chevron: [
    'm9 5 7 7-7 7'
  ],
  fire: [
    'M12 22a7 7 0 0 0 7-7c0-2.5-1.5-4-3-5.5-.9-.9-1.5-2.2-1.7-3.5-2 1-3.2 3-3.3 5-.9-.4-1.5-1.1-1.8-2C7.7 10.7 5 12.9 5 16a6 6 0 0 0 7 6Z'
  ]
}

const iconPaths = computed(() => paths[props.name] || paths.help)
const pixels = computed(() => {
  const value = Number(props.size)
  return Number.isFinite(value) && value > 0 ? value : 20
})
</script>

<template>
  <svg
    class="icon"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    :width="pixels"
    :height="pixels"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <path v-for="(d, index) in iconPaths" :key="index" :d="d" />
  </svg>
</template>

<style scoped>
.icon {
  display: block;
  flex: none;
  vertical-align: middle;
}
</style>
