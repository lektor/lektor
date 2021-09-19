module.exports = {
  env: {
    browser: true,
    es2021: true,
  },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended",
  ],
  parser: "@typescript-eslint/parser",
  settings: {
    react: {
      version: "detect",
    },
  },
  plugins: ["@typescript-eslint", "react"],
  rules: {
    "react/prop-types": 0,
    "react/button-has-type": "error",
    "@typescript-eslint/no-explicit-any": 0,
  },
};
