# Who uses this, and how we know

The Galaxy download counter is the only adoption number this project gets for
free, and it does not measure what people assume. A pipeline reinstalling the
collection on every run weighs exactly as much there as a team using it daily.
Steering a milestone on that number means optimising something nobody can read.

So this file holds what is actually known, one line per use, and **every line
names where it was said**. A use nobody can point at is a claim, not a
measurement, and this repository does not publish claims as measurements.

The counters in the root README are computed from this file. Adding a line here
is what changes them.

## Recorded uses

<!-- adoptants:début -->
None recorded yet. The place to add one is below, and it takes a sentence.
<!-- adoptants:fin -->

## Chains contributed by other people

<!-- enchainements:début -->
None yet. Every shipped playbook was written by the maintainer.
<!-- enchainements:fin -->

## Tell us yours

Two ways, neither of which is opening a bug report:

- **[Show and tell](https://github.com/stephrobert/collection-scaleway/discussions/categories/show-and-tell)**:
  say what you automate with it. One sentence is enough, and it is the entry
  that ends up here;
- **[Q&A](https://github.com/stephrobert/collection-scaleway/discussions/categories/q-a)**:
  ask. A question from someone using this for real is worth more to the project
  than a download.

If your run is under an employer who would rather not be named, say so and the
line here will read "a team in <sector>, unnamed at their request", with the
discussion as its source. What matters is that someone can follow the link and
see a person said it.

## What this file does not know

- **how many people use it.** Downloads are not users, and this file only holds
  what someone chose to tell us. The real number is larger and unknowable;
- **whether a recorded use is still current.** A line records what was true on
  its date. Nothing here expires on its own;
- **what people tried and abandoned.** The most useful feedback this project
  could get is the one it is least likely to receive.

## How a use becomes a recipe

A chain someone else wrote reaches the shipped playbooks by the route in
[CONTRIBUTING.md](CONTRIBUTING.md#from-your-chain-to-the-recipe-chapter). The
short version: it ships as a playbook, `mise run integration` plays it on every
run, and its recipe says what it refuses to do. A chain that only lives in a
discussion helps one person; a chain that ships helps everyone and stays
correct, because something replays it.
