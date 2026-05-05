# Add a New Contact

> If you have a `remember-cli` skill of your own at `.claude/skills/remember-cli/SKILL.md`, it can handle recipient discovery via Remember (리멤버, `rememberapp.co.kr`). autoreachout does not ship a `remember-cli`; bring your own, or add contacts manually.

### `add`, Add a new contact

**Before adding, MUST run safety checks (see below).**

1. Generate slug from name (lowercase, hyphens, no special chars)
2. Run dedup check (LinkedIn URL + name + company)
3. Run rate limit check
4. If checks pass: create `.md` file with full frontmatter (status: `draft`)
5. Run `uv run python scripts/build_index.py`

## Safety Checks (enforced before any `add`)

### Rate Limits

Computed from `sent_at` timestamps in the generated YAML.

| Window     | Hard limit | Warning threshold |
|------------|-----------|-------------------|
| Last hour  | 20        | 10                |
| Last 24h   | 50        | 30                |
| Last 7 days| 100       | 70                |

Hard limit → BLOCK. Warning threshold → WARN but allow if confirmed.

### Dedup Rules

1. **LinkedIn URL exact match** → BLOCK
2. **Name fuzzy match** (case-insensitive, ignoring middle names) → WARN
3. **Same company, different person** → INFORM
