import js from "@eslint/js";
import ts from "typescript-eslint";
import vue from "eslint-plugin-vue";

// Flat config (ESLint 9). `vue/flat/essential` covers correctness rules only —
// no stylistic noise — so it complements (rather than fights) the formatter.
export default ts.config(
  { ignores: ["dist/", "node_modules/", "*.config.*"] },
  js.configs.recommended,
  ...ts.configs.recommended,
  ...vue.configs["flat/essential"],
  {
    files: ["**/*.vue"],
    languageOptions: {
      parserOptions: { parser: ts.parser },
    },
  },
  {
    rules: {
      // The codebase deliberately uses `any` for loosely-typed API payloads.
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
      "no-empty": ["error", { allowEmptyCatch: true }],
      "vue/multi-word-component-names": "off",
    },
  },
);
