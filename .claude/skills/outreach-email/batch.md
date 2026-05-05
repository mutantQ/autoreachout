# Batch Drafting Mode

## Batch Drafting Mode

When drafting connection notes for multiple targets in one session, use parallel sonnet subagents to maximize speed and cross-draft quality.

### Batch Process

**Phase 1: Batch Pre-Check**
Run dedup and ecosystem collision checks for ALL targets before drafting any. Present the full check results to the user. If any target is blocked or has collision warnings, resolve before proceeding.

**Phase 2: Parallel Drafting (N agents)**
Launch one sonnet subagent per target (up to 10 in parallel). Each subagent receives:
- The target's name, company, role, LinkedIn URL, and audience type
- The "why would they reply" motivation identified in Phase 1
- A specific connection note pattern to use (rotate patterns across the batch, no two targets should use the same pattern)
- Your project's known-facts list (product, milestones, pricing, scope boundaries)
- All connection notes drafted earlier in this session (to avoid repetition)
- Explicit instruction: draft connection note only, ≤300 characters, follow all style rules

Each subagent returns: the connection note draft with character count.

**Phase 3: Parallel Review (2N + 1 agents)**
Launch all review agents in parallel. For a batch of N drafts:

| Agent type | Count | Scope | Cognitive mode |
|-----------|-------|-------|---------------|
| Fact-check | N (one per draft) | Verify claims about the recipient via web search. Role, company, quotes, product names, achievements. Mark each [VERIFIED], [LIKELY], [UNVERIFIED]. | External verification |
| Overstatement | N (one per draft) | Check the draft's claims against your project's known-facts list. Pre-production vs shipping, MOU vs customer, scope boundaries. Flag superlatives, inferences stated as fact. | Internal verification |
| Cringe / tone | N (one per draft) | Style violations: em-dashes, AI phrases ("would love to connect"), flattery formulas ("would value your perspective"), rhetorical setups, CTAs in connection notes, label-colons, cringe words. | Style enforcement |
| Recipient perspective | N (one per draft) | Fully embody the recipient. Would they accept this connection? Is it personalized enough? Does it reference something specific about THEM? Does it feel like mass outreach or a real person reaching out? Is the technical depth appropriate for their background? | Persona immersion |
| Template detection | 1 (receives ALL drafts) | Cross-draft repetition, identical openings, pattern reuse, repeated key phrases. Also check ≤300 chars, no email/CTA/signature per draft. | Cross-batch pattern scan |

**Phase 4: Consolidate + Fix**
After all 4N + 1 agents return:
- Consolidate all findings into a single results table
- Fix failing drafts directly (most template fixes are word swaps, not full rewrites)
- Only relaunch per-draft review agents if a rewrite introduces substantial new claims
- Present all drafts together for user approval

### Batch Constraints

- Maximum 10 drafts per batch (beyond this, split into multiple batches)
- Each draft in the batch MUST use a different connection note pattern (Pattern 1-5)
- If more than 5 drafts, patterns can repeat but opening structure must still vary
- Run ecosystem collision check across the ENTIRE batch, not just against existing contacts
- If 3+ targets in the batch are in the same ecosystem, warn the user before drafting

---

## Batch Awareness & Staggering Rules

These rules prevent ecosystem poisoning and apply to both single and batch drafting.

| Constraint | Rule |
|-----------|------|
| Same company | Never send to 2+ people at the same company on the same day. Stagger by 1+ week. Messages must be substantially different. |
| Same ecosystem | If 3+ contacts attend the same conferences / work on the same standard / are likely to know each other, limit to 2 per week with varied message structure. |
| Same journalist beat | Vary message structure significantly across journalists on the same beat. They may share leads. |
| Daily type limit | Flag when composing more than 3 messages of the same audience type in a single session. |
| Implementation | Query `outreach/cold_contacts.yml` for `sent_at` dates and `tags` before each draft. If ecosystem clustering is detected, warn the user. |

---

## Post-Generation Validation (Subagent Review)

Do NOT present drafts until all reviews return clean. When drafting follow-up messages (after acceptance/reply), run the same review process.

### Review Architecture: 4N + 1 Agents (all parallel)

**CRITICAL: Always spawn exactly 4N + 1 separate agents. NEVER consolidate multiple review types into a single agent. Each agent must have ONE job. Consolidating reduces review quality because agents cut corners when given multiple objectives. This is a hard rule, not a suggestion. If N=3, spawn 13 agents. If N=5, spawn 21 agents.**

For N drafts (single draft = N=1, batch = N>1):

**Agent 1: Fact-Check (N agents, one per draft)**

Prompt: "Verify every claim about the recipient against available sources. For each claim, mark [VERIFIED], [LIKELY], or [UNVERIFIED]. Check: role, company, product names, quotes, achievements, competitive intelligence, statistics. Also verify the LinkedIn URL in the .md frontmatter resolves (not a 404). Search the web to confirm. Return a list of all claims with confidence levels and sources."

**Agent 2: Overstatement (N agents, one per draft)**

Prompt: "Check claims about your project against your project-specific known-facts list (maintained privately, not in this skill). The list should cover product maturity (pre-production vs shipping), pricing the project publishes, scope boundaries (what the product does vs related-but-different things it doesn't), confirmed partnerships, team size, ship date. Flag: superlatives, inferences stated as fact, paraphrases that shift meaning, maturity overclaims ('closes this gap' vs 'building to close'), mislabeling of scope, naming partnerships not on the confirmed list."

**Agent 3: Cringe / Tone (N agents, one per draft)**

Prompt: "Check for mechanical style violations: em-dashes (,  or --), AI-typical phrases ('would love to connect', 'would value your perspective', 'I hope this finds you well'), flattery formulas, rhetorical setups disguised as questions, CTAs in connection notes ('worth a chat?', 'worth a conversation?'), label-colons ('The gap:'), cringe words (nailed, resonated, literally, invaluable), presumptuous integration proposals, pilot commitment asks. Return PASS or list of violations with specific quotes."

**Agent 4: Recipient Perspective (N agents, one per draft)**

Prompt: "You ARE [recipient name], [their role] at [their company]. [Include 2-3 sentences of specific context about the recipient.] You are reading a cold LinkedIn connection note from a stranger. Fully inhabit this perspective. Would you accept? Check: Does this reference something specific about YOU, not just your company? Does it feel like a real person reached out, or mass outreach? Is the technical depth appropriate for your background? Does it imply your product is a stopgap or incomplete? Does it assume you haven't already thought about this problem? Is it personalized enough that you'd remember it tomorrow?"

**Agent 5: Template Detection (1 agent, receives ALL drafts)**

Prompt: "Read ALL draft outreach messages from this batch. Check each draft: ≤300 chars, no email, no CTA, no signature, no em-dashes, language consistency (Korean body = Korean sign-off). Check across drafts: repeated phrases are only a violation if the two recipients are likely to know each other (same ecosystem, same conferences, same standards body, same newsroom). Identical opening structures and pattern reuse should always be flagged regardless. If reviewing follow-ups: duplicate CTAs, word count under 200. Return PASS or list of violations with specific quotes."

### After All Return

- If all return clean: present drafts to user
- If any flag issues: fix directly (most are word swaps), then present with a note explaining changes
- If [UNVERIFIED] claims exist: present to user for confirmation before finalizing
- Only relaunch per-draft agents if a rewrite introduces substantial new factual claims
- Never suppress subagent findings

### Additional Manual Checks (run alongside subagents)

These are quick checks that don't need a subagent:

1. **Connection note ≤300 characters** (count it)
2. **LinkedIn URL** included in .md frontmatter and verified not 404 (fact-check agent handles this)
3. **display_name** included in .md frontmatter
4. If drafting a follow-up: under 200 words, AI disclosure per context rules, sign-off format correct
