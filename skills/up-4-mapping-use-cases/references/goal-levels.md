# Goal levels

How to tell whether a candidate is a use case, with accepted and rejected
examples for screens, interfaces between systems, and scheduled work.

## Three levels

| Level | What it is | In this method |
|---|---|---|
| Summary | An area of work across several sittings, often several roles | A business process model, tested by journey test cases. Never a use case specification |
| User goal | What one actor wants from the system now | A use case. Everything in the diagram is at this level |
| Subfunction | A partial goal that exists only to serve user goals | A step inside a use case |

## The test for a user goal

All of these hold:

- One actor pursues it.
- In one place, at one time: one sitting of a couple of minutes up to about
  twenty.
- When it is done the actor can walk away with something of value.
- The actor would name it as a reason to use the system.

For a scheduled or system-triggered goal, replace "sitting" with "run": one
trigger, one run, a result someone relies on.

## Finding the level

**Suspect it is too low?** Ask *why is the actor doing this?* The answer is a
goal one level up. Keep asking until the answer is something the actor would
come for.

```text
Enter card number   → why? → to pay for the order
Pay for the order   → why? → to get the goods        ← a user goal: Place Order
```

**Suspect it is too high?** Ask *how?* If the answer is a list of things done
in separate sittings or by different people, the candidate is a summary.

Most first drafts are too low. A list with many more than eight goals for a
small service is the usual symptom.

## Signs of a summary hiding in a use case

Any one of these in the intended flow:

- The work is handed to another role ("then the assessor reviews it").
- The flow waits for something outside: an answer by mail, a deadline, a
  delivery.
- Branches run in parallel for different actors.

Each role's part becomes its own use case. The connection between them is the
business process: its activities are use cases, and each path through it
becomes a journey test case. Do not describe the process inside any use case.

## Accepted and rejected

| Candidate | Verdict | Why, and what to do |
|---|---|---|
| Borrow Book | Use case | A member comes for it and leaves with a book |
| Validate ISBN | Subfunction | A step of *Add Book to Catalog* |
| Search Customer | Subfunction, usually | Nobody comes only to search; a step of the goals that need a customer. A use case only if finding is itself the value (a directory) |
| Log In | Use case, small | Establishes the precondition of many others. Do not draw includes to it |
| Manage Customers | Use case while operations share one shape | Split out an operation when it gets its own rules |
| Process Insurance Claim | Summary | Clerk records, assessor decides, payout follows approval: three use cases and a process |
| Run Month-End | Summary | Split by what each role or run achieves |
| Export Invoices Nightly | Use case | Actor: Scheduler. Trigger: a time. Result: the accounting system has the invoices |
| Receive Payment Notification | Use case | Actor: Payment Provider (external system). Trigger: its message. Result: the order is marked paid |
| Retry Failed Deliveries | Subfunction or use case | A step of the sending use case if it only repeats it; its own use case if someone relies on its result and it has its own rules |
| Create Loan Record | Wrong language | The developer's phrase for *Borrow Book* |
| Health Check, Metrics | Not a use case | Operational plumbing with no actor goal; a non-functional requirement if it matters |

## Naming

- A short active verb phrase: verb, then object. *Approve Estimate*.
- In the words of the actor, not of the code or the database.
- An actor never comes to "manage" something as such. *Manage X* is an
  accepted shorthand for a group of small operations and nothing else.
- The name is an interface: it appears in the diagram and, lowercased with
  hyphens, in the file name. Choose it once.

## Functional requirements and use cases

- Every use case realizes at least one functional requirement.
- Every functional requirement in scope is realized by at least one use case.
- A requirement that describes a step, not a goal, traces to the use case that
  contains the step. It does not get a use case of its own.
- One requirement may need several use cases, and one use case may realize
  several requirements.
