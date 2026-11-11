# The invention list

You are the only one who knows what you had to decide on your own. A reviewer
sees finished code in which your inventions look like everything else. So you
write them down, before coding and again after.

An invention is any decision you make that the use case, its linked
requirement rows, the entity model and the guideline file did not make for
you.

A name or signature the specification leaves open (function, module, file or
parameter) is a technical choice (rule 8): pick one, list it in the invention
list and go on. Where the specification names an interface, its names bind.
Ask about a behavior decision that changes an outcome that the request or specification names; otherwise record the closest reading as an assumption and name it in the handoff.

## The four tags

| Tag | Test | What happens to it |
|---|---|---|
| `behavior` | Does the choice change what an actor does or what the system answers? | Record a reading; ask if it changes a named outcome. The answer goes into the specification |
| `data` | Is the shape or meaning of a business noun undefined? | Ask. The answer goes into the entity model |
| `mechanism` | Is it only about how the system is built, including an unspecified name or signature? | Decide from the guideline file and existing code. A new project-wide choice goes into the guideline file; a one-off into a decision record |
| `free` | Nobody could tell the difference, or the specification leaves it open on purpose (a label or a layout) | Decide, list it, move on. It may differ in another implementation |

When unsure between `behavior` and `free`, it is `behavior`. Unspecified
names and signatures are `mechanism`; do not turn them into behavior questions.

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

For every unanswered behavior item, choose the reading closest to the specification and record it in the invention list as an assumption. Ask when the choice changes an outcome that the request or specification names, most consequential first. Otherwise use the recorded reading. Never decide silently; name the recorded reading in the handoff. The answer goes into the specification. If the owner says to continue without answering, implement the recorded reading. While a required behavior answer has not arrived, that behavior stays unimplemented unless the owner authorizes the recorded reading, and the independent authorized work goes on. Do not ask about mechanism.

## Where the list lives

In the pull request description, using the plan template. Never in the
specification file: decisions go there as specification text, not as a log.

## After coding

Go through the diff once more and add what you only noticed while writing.
Then check: is there anything in the code that a reviewer would be surprised
by? If yes, it belongs on the list.
