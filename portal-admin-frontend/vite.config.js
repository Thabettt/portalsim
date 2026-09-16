import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  server: {
    port: 7890,
    strictPort: true,
  },
  preview: {
    port: 7890,
    strictPort: true,
  },
  plugins: [
    react(),
    tailwindcss(),
  ],
})

