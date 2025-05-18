import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";

// Separate from vite.config.ts so the dev/build config stays free of test typings.
export default defineConfig({
  plugins: [vue()],
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.{test,spec}.{ts,js}"],
  },
});
