# Architecture

PCPulse separates collection, models, serialization, health checks, and the CLI.

## Data flow

    Operating system
          |
          v
      Collectors
          |
          v
        Models
        /     \
       v       v
 Serialization Health checks
       |       |
       v       v
    JSON/MD   Doctor
          \
           v
          CLI

Collectors read local information and return typed models. Serialization converts those models to external formats. Health checks interpret collected values without modifying the machine. The CLI provides a user-facing interface over the library.

This separation allows downstream applications to import PCPulse instead of parsing terminal output.

## Compatibility

Platform-specific collectors should degrade gracefully. If a metric is unavailable, the model should represent it as unavailable rather than guessing.

Public schema changes should be documented and versioned deliberately.
