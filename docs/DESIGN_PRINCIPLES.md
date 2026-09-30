# Design Principles

## Local-first

The core functionality should work without a hosted service or mandatory network connection.

## Privacy-first

Identity information is opt-in. Diagnostic output should be treated as potentially sensitive even when PCPulse itself does not transmit it.

## Structured output

JSON and typed Python objects are first-class interfaces. Human-readable terminal output is useful, but applications should use the library or structured formats.

## Best-effort collection

Operating systems expose different metrics. PCPulse should report unavailable values rather than fabricate data.

## Read-only diagnostics

Collectors should observe the host rather than silently modifying it.

## Compatibility

Changes to public APIs, output schemas, and command behavior should be deliberate and documented.

## Maintainability

The project should prefer understandable implementations and a small dependency surface over unnecessary complexity.
