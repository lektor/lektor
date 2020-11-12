module.exports = {
  env: {
    browser: true,
    es2021: true,
  },
  extends: ["eslint:recommended", "plugin:react/recommended"],
  parserOptions: {
    ecmaFeatures: {
      jsx: true,
    },
    ecmaVersion: 12,
    sourceType: "module",
  },
  settings: {
    react: {
      version: "detect",
    },
  },
  plugins: ["react"],
  rules: {
    "no-undef": 0,
    "no-unused-vars": 0,
    "react/no-string-refs": 0,
    "react/no-unescaped-entities": 0,
    "react/prop-types": 0,
  },
};
