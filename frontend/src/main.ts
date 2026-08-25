import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import './style.css'

// The locked viewport in index.html stops double-tap zoom everywhere, but iOS Safari
// deliberately ignores `user-scalable=no`. Refusing Safari's own pinch gestures is the only
// thing that makes a phone browser behave like an installed app; scrolling is untouched.
for (const event of ['gesturestart', 'gesturechange', 'gestureend']) {
  document.addEventListener(event, (e) => e.preventDefault())
}

createApp(App).use(createPinia()).use(router).mount('#app')
