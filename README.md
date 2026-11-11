# Plan Review — Castar Conversion Indexer

**Role:** Founding Payments Engineer · **Format:** plan review, verbal · **Time:** 60 min

## Context

We build with coding agents like Claude Code, and the plan an agent writes before it
starts coding is the cheapest place to catch a mistake.

[`castar-conversions/`](./castar-conversions/) is a tiny version of Castar's
conversions service:
1. A customer sends one stablecoin to Castar's treasury wallet.
2. Castar swaps it on Uniswap.
3. Castar pays the other stablecoin out to the customer.

Today ops checks each deposit by hand and runs the swap and payout with a
command. One of our engineers asked Claude Code to plan an **indexer** that does
this on its own: it watches Ethereum and Base, identifies deposits and our own
swaps and payouts, and moves each conversion along. We'll share `PLAN.md`, with
the engineer's request and the plan the agent produced, during the interview.
Nothing has been built yet.

You're the engineer who has to sign off before implementation starts. The
plan has **bugs**, and some of them are subtle. Expect to read the plan's code
carefully, and to check it against the codebase.

## Your task

1. **Read the codebase.** Take about 10 minutes, starting with its README. It's
   small on purpose.
2. **Read the request and the plan.** Take about 20 minutes. Think out loud if you
   like.
3. **Find the problems.** Anything that would lose or misdirect money, leave a
   conversion stuck, hide a failure, or not do what the request asked.
4. **Prioritize** them by how much they'd hurt if this shipped, and say why.
5. **Explain how you'd fix each one**, concretely enough that the agent could act on
   it.

Then we'll discuss: would you approve this plan, send it back, or start over? What
would you tell the agent? And what would you change about the original request?

## Working notes

- Ask the interviewer anything you'd ask the engineer who wrote the request, about
  our customers, the treasury, Uniswap, or the chains in use. They'll answer as
  that engineer.
- You don't need to know Uniswap's or Alchemy's APIs by heart. If a detail matters,
  ask.
- Not everything in the plan is wrong. Saying which parts you'd keep is part of a
  good review.
- The toy codebase cuts corners on purpose (auth, schemas, migrations, key
  management). Don't sweat that. Focus on the plan at hand.
- We care about how you triage at least as much as how many problems you find.
