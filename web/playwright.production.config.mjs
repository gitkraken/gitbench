export default Object.freeze({
  targetUrl: 'https://gitbench.gitkraken.com/',
  measurementId: 'G-5SDMWDGT2G',
  observationTimeoutMs: 30_000,
  maxAttempts: 2,
  browser: Object.freeze({
    headless: true,
    serviceWorkers: 'block',
  }),
});
