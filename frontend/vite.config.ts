import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],

  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },

  build: {
    // O Three é distribuído como um módulo monolítico (~676 kB minificado);
    // as rotas e os demais vendors ficam em chunks separados e cacheáveis.
    chunkSizeWarningLimit: 700,
    rolldownOptions: {
      output: {
        codeSplitting: {
          includeDependenciesRecursively: false,
          groups: [
            { name: "three-addons", test: /node_modules\/three\/examples\//, priority: 45 },
            { name: "three", test: /node_modules\/three\//, priority: 40 },
            { name: "react", test: /node_modules\/(?:react|react-dom|scheduler)\//, priority: 35 },
            { name: "react-three", test: /node_modules\/@react-three\//, priority: 30 },
            { name: "d3", test: /node_modules\/(?:d3|d3-[^/]+|internmap|delaunator|robust-predicates)\//, priority: 20 },
          ],
        },
      },
    },
  },
})
