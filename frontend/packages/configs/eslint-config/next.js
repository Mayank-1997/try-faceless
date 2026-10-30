/** @type {import('eslint').Linter.Config} */
module.exports = {
  extends: ['./next.js'],
  rules: {
    '@next/next/no-html-link-for-pages': 'off',
  },
}
