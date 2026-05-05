---
slug: ravi-deshmukh
name: Ravi Deshmukh
company: Truthline Forensics
role: Principal Examiner
linkedin: https://www.linkedin.com/in/example-ravi-deshmukh/
channel: linkedin
method: connection-note
display_name: Founder
subject: hardware-anchored video for court admissibility
status: met
contact_type: cold
related_to: acme
vertical: forensic
tags: [forensic, video-authentication, court]
sent_at: "2026-03-30"
accepted_at: "2026-03-31"
last_replied_at: "2026-04-02"
meeting_at: "2026-04-15T22:00:00+09:00"
met_at: "2026-04-15"
notes: "Principal video examiner at a US forensic firm. Met April 15 (30 min). Strong fit on the court-admissibility framing; offered to red-team an eval unit. Pre-production unit ship pending."
---

## Sent (connection note)

Ravi, courtroom video authentication still leans on heuristics for capture integrity. Acme signs every frame in dedicated hardware before the OS, so tampering breaks the signature chain. Pre-production, Q3 ship. Worth a short conversation?

## Reply received (2026-04-02)

Yes. Tuesday 9am ET works for me, send a Meet link.

## Meeting completed (2026-04-15, 30 min)

Discussion landed on three points. First, court admissibility is the highest-value framing for forensic examiners and the messaging should lead with it. Second, Ravi offered to red-team an eval unit (exhaustive tamper attempts) at no cost. Third, trusted timestamping plus hardware signing is the combination that examiners testify on; expose timestamp metadata in the verifier output.

## Open actions

- Ship pre-production eval unit when ready (target: late June)
- Add timestamp metadata to the verifier output; confirm with Ravi
- Send a written tech brief covering signing chain, key custody, and timestamp source
