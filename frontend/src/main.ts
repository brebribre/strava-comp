import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import './style.css'
import { useTheme } from '@/hooks/useTheme'

const app = createApp(App).use(createPinia()).use(router)

// Applied before mount so the saved accent is in place on the first paint rather than
// flashing monochrome first.
useTheme().restore()

app.mount('#app')
