# Claude Code Usage Report

This folder will contain a stdlib-only usage report script that shows:

1. **Total cost** for the current period
2. **Cache-read share of input tokens** for the last 7 days (a drop after rollout means something is breaking the cache)
3. **Cost by agent type** if the usage data includes agent identity

## Usage

```bash
python scripts/claude_usage/report.py
```

## Expected Output Format

```
=== Claude Code Usage Report ===
Period: <date range>

Total Cost: $<amount>
Cache-Read Share: <percentage>% of input tokens

Per-Agent Cost:
  <agent-type>: $<amount> (<percentage>%)
  ...

Note: If per-agent breakdown is unavailable on this version, it will be noted.
```

## Implementation Notes

- Uses only Python standard library (no external dependencies)
- Reads usage data from the platform's usage export or API
- Supports first-party API, Vertex AI, Bedrock, and Foundry platforms
- Cache-read share is calculated as: `(cache_read_tokens / total_input_tokens) * 100`