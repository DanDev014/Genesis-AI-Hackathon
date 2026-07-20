import type { FlatConfigComposer } from "../node_modules/.pnpm/eslint-flat-config-utils@3.2.0/node_modules/eslint-flat-config-utils/dist/index.mjs"
import { defineFlatConfigs } from "../node_modules/.pnpm/@nuxt+eslint-config@1.16.0_@typescript-eslint+utils@8.61.0_eslint@10.7.0_jiti@2.7.0__ty_7175df7e91f9ac5d16a7aef44d828128/node_modules/@nuxt/eslint-config/dist/flat.mjs"
import type { NuxtESLintConfigOptionsResolved } from "../node_modules/.pnpm/@nuxt+eslint-config@1.16.0_@typescript-eslint+utils@8.61.0_eslint@10.7.0_jiti@2.7.0__ty_7175df7e91f9ac5d16a7aef44d828128/node_modules/@nuxt/eslint-config/dist/flat.mjs"

declare const configs: FlatConfigComposer
declare const options: NuxtESLintConfigOptionsResolved
declare const withNuxt: typeof defineFlatConfigs
export default withNuxt
export { withNuxt, defineFlatConfigs, configs, options }