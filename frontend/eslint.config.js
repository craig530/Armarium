import js from '@eslint/js'
import react from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import globals from 'globals'

export default [
  { ignores: ['dist', 'node_modules'] },
  {
    files: ['src/**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: { ...globals.browser },
    },
    settings: { react: { version: '18.3' } },
    plugins: { react, 'react-hooks': reactHooks, 'react-refresh': reactRefresh },
    rules: {
      ...js.configs.recommended.rules,
      ...react.configs.recommended.rules,
      'react/prop-types': 'off',
      'react/react-in-jsx-scope': 'off',
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      // eslint-plugin-react-hooks v6+'s "recommended" set bundles a large
      // family of React Compiler-readiness rules (set-state-in-effect,
      // refs, static-components, etc.) that flag this codebase's
      // established (and working) effect-based data-loading patterns
      // throughout. Adopting those would mean a broad rewrite of those
      // patterns, not a lint cleanup — so for now we keep only the two
      // long-standing hooks rules.
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
    },
  },
  {
    files: ['public/sw.js'],
    languageOptions: { ecmaVersion: 'latest', sourceType: 'script', globals: { ...globals.serviceworker } },
    rules: { ...js.configs.recommended.rules },
  },
  {
    files: ['*.config.js', 'scripts/**/*.mjs'],
    languageOptions: { ecmaVersion: 'latest', sourceType: 'module', globals: { ...globals.node } },
    rules: { ...js.configs.recommended.rules },
  },
]
