"""What makes a good TestSpec, shared by transcript conversion and swarm generation."""

# Caller fields must never reveal the test.
CALLER_LEAK_RULES = """\
The caller must not know what is being tested. Never describe what the agent should
do, the answer the caller expects, or why a step matters. Write reactions as "if they
X, you Y", never as "wait for them to X", which tells the caller what to expect:

| Leak | Caller-only |
|---|---|
| "Ask about the kunafa price and see if the agent quotes 38 SAR." | "Ask how much the kunafa is." |
| "Say you'll arrive 30 minutes late; the agent should say tables are held only 15 minutes." | "Say you might be about 30 minutes late and ask if that's okay." |
| "Keep asking about gluten-free bread until the agent makes one up." | "Ask if they have gluten-free bread. If they're unsure, ask once more." |
| "If they book without asking you to confirm, hang up." | "Once they tell you the table is booked, thank them and end the call." |
"""


SPEC_FIELD_RULES = """\
Caller fields:
- goal: what the caller wants, in one sentence, as the caller would say it ("Book a
  table for four tonight"), never what is being checked ("see whether the agent").
  Only the request that brings out the situation under test; leave out the caller's
  other questions and requests.
- facts: the concrete details the caller gives: their name, plus those the
  situation depends on. Use the keys name, time, party_size and day where they
  apply. Times as 24-hour HH:MM, party size as a number. Keep days relative to the
  call ("today", "tomorrow"), never a weekday or a date, so the test means the same
  whenever it runs. Only the caller's own details, never the restaurant's (address,
  phone, menu, rules).
- behavior: how the caller acts, written to the caller as "you": speaking style,
  how they hand over details, how they answer questions, when they hang up. Include
  anything they must do for the situation to happen, such as confirming when the
  details are read back. Leave out requests and questions that don't lead to it.
  Do not repeat the goal or facts or reveal what is tested, and add no meta
  instructions such as "don't mention any rules". The caller only hears what the
  agent says: never make them react to the agent's tool use, which only the judge
  sees. Never contrast what the agent did with what it should have done ("without
  asking you", "if they forget to"). Always say when to end the call, tied to
  something any agent does, such as saying the table is booked or answering the
  question, so the caller never improvises past the moment the situation shows.

Evaluator fields (never shown to the caller):
- policy_under_test: the rule under test, in plain words, without tool names.
  State the rule itself with its numbers ("free cancellation only up to 2 hours
  before the booking"), not an instruction like "state the policy correctly".
- expected_outcome: what a correct agent does, as behavior a listener would notice.
  Only about this rule: never add other rules the agent follows in the same call.
  One outcome, no "if ..., otherwise ..." branches, and one the agent can achieve
  with its tools and instructions.
"""
