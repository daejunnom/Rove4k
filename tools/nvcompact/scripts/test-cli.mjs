// Public node:test API works on both Node 22 and Node 24, without a
// version-specific --test-isolation flag or nested worker requirement.
await import('../npm/tests/cli.test.mjs');
