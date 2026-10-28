# Teaching demo: Python loops, expenses and Fibonacci

This script follows the highlighted 25–40 minute teaching demo in the lesson plan. Times below are relative to the start of the demo. The five-minute individual coding period is part of the 15 minutes. Prepare the group's editor/submission platform and Mentimeter in advance; use a show of hands, local Python and a TA submission log if needed.

## Slide 1 — Poll 1: range (0–1 minute)

“Let's start with a quick poll. How many times does this loop run? Vote individually: three, four, or five.”

(Wait for all four students to vote. Invite one to explain. Reveal the answer.)

“`range(1, 5)` gives 1, 2, 3 and 4. The stop value 5 is excluded, so there are four iterations. We'll use that idea of repetition in a problem we've already seen.”

## Slide 2 — Worked example: expenses (1–4 minutes)

“Imagine the expenses are 18, 25, 32 and 15. What action repeats when we calculate their total?”

(Invite a student to answer.)

“We take the next expense and add it to the running total. Let's turn that into a loop. First initialize `total` to zero, before the loop. Then, for each expense, update the total. Once the loop finishes, print it.”

(Point to each line and its indentation. Click the animation one iteration at a time.)

“Before I click, predict the new total. First we add 18: the total is 18. Add 25 and it becomes 43. Then add 32: 75. Finally add 15: 90. Why do we initialize outside the loop? Because we want to preserve the running total across iterations. Why is `print` outside? Because we want the final total once.”

## Slide 3 — Poll 2: reset error (4–5 minutes)

“Now look closely at the indentation. What will this version print: 90, 15, or 0? Vote individually.”

(Collect all four votes and ask a student for the reasoning. Step through the animation, then reveal.)

“It's 15. On every iteration, `total` is reset to zero before we add the current expense. Only the last expense survives. How would you repair it?”

(Invite an answer.)

“Move `total = 0` before the loop. That initializes once and preserves the value between iterations.”

## Slide 4 — Introduce the Fibonacci task (5–6 minutes)

“Now we'll transfer the idea of updating state to a different problem. The Fibonacci sequence starts 0, 1, 1, 2, 3, 5: each new term after the first two is the sum of the previous two.

“Your task is to complete this function so it returns the first `n` terms. Start with an empty list and the two state variables shown. You may copy the starter from the slide, or use the starter prepared in your editor. Test the edge cases: `n = 0` must return an empty list, `n = 1` must return `[0]`, and `n = 8` must return the eight terms shown. You will work individually in your Python editor.”

## Slide 5 — Individual coding (6–11 minutes)

“You have five minutes. Implement a loop, run all three tests, and submit through our group's chosen method. Be prepared to explain one update of your state variables.”

(Click “Start timer” on the slide. It displays a one-minute warning and can be paused or reset. The TA circulates. Ask questions rather than providing the solution: “Which value do you append?” “What are the current and next terms?” “How do you preserve the old values?” Give a one-minute warning. Record submissions and verification times; use local Python and a TA log if the platform fails.)

“Please submit what you have now. We will discuss the state update together.”

## Slide 6 — Student explanation and bug (11–13 minutes)

“Could someone explain their solution and walk us through one iteration?”

(Invite a student. Then show the faulty sequential update.)

“Suppose `a` is 0 and `b` is 1. After `a = b`, what are the values? Both are 1. Now `b = a + b` uses the new `a`, so `b` becomes 2. We get `(1, 2)`, but the desired next pair is `(1, 1)`.

(Use “Append and update” to animate several correct state transitions. Pause on each pair and ask students which old values produced it.)

“We need both old values to calculate the next pair. Python's simultaneous assignment `a, b = b, a + b` evaluates the right-hand values before assigning them, so the old pair is preserved for the calculation.”

(Optional instructor reference solution, reveal verbally only after the independent task.)

```python
def fibonacci(n):
    result = []
    a, b = 0, 1
    for _ in range(n):
        result.append(a)
        a, b = b, a + b
    return result
```

## Slide 7 — Verified results (13–14 minutes)

“The TA will verify the submissions: the solution must use a loop, pass the tests for 0, 1 and 8, and the student must explain a state update.”

(Show the real leaderboard or TA log. Recognize the earliest verified correct submission and give the small reward if available. Do not announce a winner before verification.)

## Slide 8 — Quick check and summary (14–15 minutes)

“One final check for everyone: what should `fibonacci(1)` return, and why?”

(Collect responses, then reveal.)

“It returns `[0]`: one iteration appends the first term exactly once. Across both examples, the pattern is initialize, repeat, update, and test. The important question is which values must be preserved between iterations. Next, we'll transfer the loop to a related sequence and complete an individual exit check.”

## Timing

| Demo time | Activity |
|---|---|
| 0–1 | Poll: `range(1, 5)` |
| 1–4 | Build and trace the expense loop |
| 4–5 | Poll: reset inside the loop |
| 5–6 | Introduce Fibonacci starter and tests |
| 6–11 | Individual coding; TA prompts and one-minute warning |
| 11–13 | Student explanation and sequential-update bug |
| 13–14 | Verify results and recognize the earliest correct submission |
| 14–15 | Check `n = 1` and summarize |
