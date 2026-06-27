# Preview screenshots

Drop submission screenshots here (PNG). These feed the Devpost "in action" images,
the demo video, and the deck. Capture clean, full-resolution shots.

## Shot list (capture these)

Agent (done / in progress):
- [ ] Published v1.0.0 panel (Change history → "Published v1.0.0", Orchestrator Tenant)
- [ ] Verdict 1 — `real_defect` (Checkout_E2E_007): output showing label + 0.97 confidence + grounded rationale + empty proposed_fix
- [ ] Verdict 2 — `flaky` (Cart_UI_012): label flaky + a proposed_fix
- [ ] Verdict 3 — `environment` (Payments_API_003): label environment
- [ ] Agent Definition canvas (system prompt + the 5 grounded input pills)
- [ ] Edit I/O Schema (inputs + outputs) showing the structured output

Platform breadth (as you build them):
- [ ] Admin → Services (Maestro, Test Manager, Actions, Orchestrator enabled)
- [ ] Maestro process graph (if built): scorer → classifier → Action Center gate
- [ ] Action Center approval task (the human-in-the-loop step)
- [ ] Test Manager / Test Cloud failing run (the data source)

Coding-agent bonus (record, don't just screenshot):
- [ ] Claude Code + `uip` CLI session: build / `uip rpa analyze` / pack / publish

## Naming
Use clear names so they're easy to drop into the deck/Devpost, e.g.:
`01-published-v1.png`, `02-verdict-real-defect.png`, `03-verdict-flaky.png`,
`04-verdict-environment.png`, `05-agent-canvas.png`, `06-maestro-process.png`,
`07-action-center.png`.
