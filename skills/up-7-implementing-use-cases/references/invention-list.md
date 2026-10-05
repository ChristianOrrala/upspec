# The invention list

You are the only one who knows what you had to decide on your own. A reviewer
sees finished code in which your inventions look like everything else. So you
write them down, before coding and again after.

An invention is any decision you make that the use case, its linked
requirement rows, the entity model and the guideline file did not make for
you.

## The four tags

| Tag | Test | What happens to it |
|---|---|---|
| `behavior` | Could a stakeholder observe the difference between two reasonable choices? Could a test assert it? | **Stop and ask.** The answer goes into the specification |
| `data` | Is the shape or meaning of a business noun undefined? | Ask. The answer goes into the entity model |
| `mechanism` | Is it only about how the system is built? | Decide from the guideline file and existing code. A new project-wide choice goes into the guideline file; a one-off into a decision record |
| `free` | Nobody could tell the difference, or the specification leaves it open on purpose (a label, a layout, an internal name) | Decide, list it, move on. It may differ in another implementation |

When unsure between `behavior` and `free`, it is `behavior`.

## Finding the items

Read each element in scope and ask what you would have to make up:

- **Shows, lists, displays:** which items, which details of each, in what
  order, how many, what if there are none?
- **Informs, confirms, notifies:** what does it say? Who receives it?
- **Validates:** against which rule exactly? Where is the boundary?
- **Records, stores, sets:** which values? What about the fields the step does
  not mention?
- **Selects, enters:** from what? What is allowed? What is the default?
- **Time words:** today, now, within, until: whose clock, which time zone,
  inclusive or exclusive?
- **A step that can fail with no flow anchored to it:** what should happen?
- **Roles:** may every instance of the actor do this to every instance of the
  thing?
- **Twice, or at the same moment:** what if the request is repeated?

Words that always produce an item: appropriately, relevant, suitable, etc.,
handles, as needed, if possible.

## Asking

One line per item, naming the element, with the readings you see and the one
you recommend:

```text
UC-012 step 7 [behavior]: "System confirms that the task was assigned."
  What does the confirmation contain?
  (a) task title and assignee's name   (recommended: matches step 2's content)
  (b) only that it succeeded
```

Ask the behavior items together, most consequential first. Do not ask about
mechanism.

If the owner answers and tells you to proceed, implement the chosen reading
and report it under "asked". The specification still has to change; say so in
the hand-off. If nobody can answer, leave that part unimplemented and say so.
Do not pick a reading silently.

## Where the list lives

In the pull request description, using the plan template. Never in the
specification file: decisions go there as specification text, not as a log.

## After coding

Go through the diff once more and add what you only noticed while writing.
Then check: is there anything in the code that a reviewer would be surprised
by? If yes, it belongs on the list.
