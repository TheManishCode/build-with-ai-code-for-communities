import '@testing-library/jest-dom/vitest'

// jsdom doesn't implement matchMedia or ResizeObserver -- the "motion" library's
// useReducedMotion() and layout-animation internals touch both unconditionally, so every
// component test needs these stubbed regardless of whether a given test exercises motion.
if (!window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia
}

if (!window.ResizeObserver) {
  window.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver
}
