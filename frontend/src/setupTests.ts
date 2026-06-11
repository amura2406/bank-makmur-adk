import '@testing-library/jest-dom';

// Polyfill Element.prototype.scrollIntoView for Vitest + jsdom environment
if (typeof window !== 'undefined' && window.HTMLElement) {
  window.HTMLElement.prototype.scrollIntoView = function () {};
}
