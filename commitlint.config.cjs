// commitlint.config.cjs
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    "subject-case": [2, "always", ["lower-case", "sentence-case", "start-case"]],
  },
};
