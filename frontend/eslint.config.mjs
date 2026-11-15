import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

const config = [
  ...nextCoreWebVitals,
  ...nextTypescript,
  {
    rules: {
      // Interface en français : l'apostrophe est omniprésente et sans ambiguïté en JSX.
      "react/no-unescaped-entities": ["error", { forbid: [">", "}"] }],
    },
  },
  { ignores: [".next/**", "node_modules/**", "next-env.d.ts"] },
];

export default config;
