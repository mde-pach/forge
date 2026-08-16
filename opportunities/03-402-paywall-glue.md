# Drop-in per-call paywall middleware (x402 + ACP)

Status: awaiting-judgment · Sweep: 2026-08-16 · Modes: new-primitive × translation (glue shape)

**Gap.** Solo devs with useful-but-tiny APIs/tools can't justify subscription infrastructure; agents as buyers just removed the transaction-cost blocker that killed micropayments for 25 years. Missing: the boring glue that makes an endpoint payable in one line.

**Evidence.** HTTP 402 desire documented since 2015 ([W3C list](https://lists.w3.org/Archives/Public/public-webpayments/2015Jun/0042.html), A2) and its blocker analyzed in 2020 ([Piszek](https://piszek.com/2020/05/19/micropayments/), B3); x402 launched May 2025, V2 2026 ([Coinbase](https://www.coinbase.com/developer-platform/discover/launches/x402), A2); Agentic Commerce Protocol Stripe+OpenAI Sept 2025 ([Stripe](https://stripe.com/blog/developing-an-open-standard-for-agentic-commerce), A2).

**Why-now.** Strongest of the sweep: both standards shipped inside 15 months; agent traffic is arriving at everyone's endpoints either to be blocked or to pay.

**Graveyard/tarpit.** Micropayments graveyard is enormous (Flattr, Coil…) — but every corpse predates the removal of the human-attention cost; the tarpit check must ask what else killed them (volatility, two-sided cold start). Standards war risk: x402 vs ACP vs whatever Google ships.

**Shape.** Solo devs and small teams with APIs/datasets/scrapers; content/tool builders who want agent traffic to pay. Large, self-serve reachable.

**Fit.** Strong shape-fit: one-line glue erasing boilerplate is exactly the unchained/lazy-depends taste. Domain (payments/crypto rails) is new territory for him — judgment call.

**Angle.** "Stripe-for-402": one package wrapping any endpoint with per-call pricing, x402 to agents, ACP/Stripe checkout to humans, revenue dashboard. Surface: TS middleware first (need is web-server-shaped), Python twin later.
