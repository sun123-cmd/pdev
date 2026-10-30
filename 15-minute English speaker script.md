# Python Loops: From Expenses to Fibonacci

A simple script for the classroom slides. Words in brackets are actions for the teacher. The times are for planning; they do not appear on the slides.

## Slide 1 — Poll: How many times? (0–1 minute)

“Let's start with a quick question. Look at this loop. How many times will it run? Is it 2, 3, 4, or 5?

“Think for a moment. Then scan the QR code and vote on your phone.”

[Wait for the live Mentimeter results. Ask one student why. Then reveal the answer.]

“The answer is 4. The values are 1, 2, 3, and 4. The loop stops before 5.”

## Slide 2 — Add the expenses (1–4 minutes)

“Now let's look at four expenses: 18, 25, 32, and 15. How can we find the total?

“What do we do again and again?”

[Let a student answer.]

“Yes. We take the next number and add it to the total. Let's use a loop.

“First, we set `total` to zero. Then we take each expense and add it. When the loop ends, we print the total.”

[Point to each line. Click through the animation. Ask students to guess the next total before each click.]

“First, 0 plus 18 is 18. Then we add 25. We get 43. Next, we add 32. We get 75. Last, we add 15. The answer is 90.

“Look at `total = 0`. It is before the loop, so it runs once. The total can grow each time. The print line is after the loop, so we print the final answer.”

## Slide 3 — Poll: What is the output? (4–5 minutes)

“Now look at this code. We have moved `total = 0` inside the loop. What will the code print? Is it 15, 18, 4, or 5?”

[Ask students to scan the new poll QR. Wait for the live results, ask a student to explain, then click through the loop and reveal the answer.]

“The answer is 15. Each time the loop runs, we set `total` back to zero. Then we add the current expense. So we lose the earlier total. At the end, only 15 is left.

“How can we fix it?”

[Let a student answer.]

“Move `total = 0` before the loop. Then it runs only once.”

## Slide 4 — Meet Fibonacci (5–6 minutes, first part)

“Now let's look at another list of numbers. It is called the Fibonacci sequence.

“It starts with 0 and 1. After that, we add the last two numbers to get the next one.

“Look at the triangle. Zero plus one is one. So we have 0, 1, 1. What comes next?”

[Let a student answer. Click “Show next triangle”.]

“Yes. One plus one is two. Now what is one plus two?”

[Click again.]

“It's three. We can keep doing the same thing. A loop can help us do that.”

## Slide 5 — The Fibonacci task (5–6 minutes, second part)

“Now it's your turn to write a function. It should return the first `n` Fibonacci numbers.

“Start with the code on the slide. You can copy it or use the code in your editor.

“Please test three cases. If `n` is 0, return an empty list. If `n` is 1, return a list with just 0. If `n` is 8, return the eight numbers on the slide.

“Work on your own. When you finish, submit your code.”

## Slide 6 — Individual coding (6–11 minutes)

“Scan the FiboLab QR, or open the link on your coding laptop. Join with your name. You have five minutes. Use a loop, then submit and check the test results. Be ready to explain how `a` and `b` change.”

[Use a separate five-minute timer. The TA moves around and asks questions.]

If a student needs help, ask:

- “Which number do you add to the list?”
- “What are `a` and `b` now?”
- “How can you keep the old values for the next step?”
- “What happens when `n` is 0?”

[Give a one-minute warning. FiboLab stores every attempt and updates the shared leaderboard every five seconds.]

“One minute left. Please test your code and submit it.”

[At the end of five minutes:]

“Please submit what you have. Let's look at the update together.”

## Slide 7 — Where did the old value go? (11–13 minutes)

“Can someone show us their answer and explain one step?”

[Invite a student. Then point to the two lines on the slide.]

“Let's start with `a = 0` and `b = 1`. After `a = b`, what is `a`?”

[Pause.]

“It's 1. And `b` is still 1. Now we run `b = a + b`. What is `b`?”

[Pause.]

“It's 2. So now we have 1 and 2. But we wanted 1 and 1. The problem is that we changed `a` too early. We lost its old value.

“We can fix this with `a, b = b, a + b`. Python works out the values on the right first. Then it updates both variables.”

[Click “Append and update” a few times. Ask students to name the old pair and the new pair.]

“Here we start with 0 and 1. We add 0 to the list. Then the pair changes to 1 and 1.”

Teacher reference, after the coding task:

```python
def fibonacci(n):
    result = []
    a, b = 0, 1
    for _ in range(n):
        result.append(a)
        a, b = b, a + b
    return result
```

## Slide 8 — Check the results (13–14 minutes)

“Let's check the submissions. We need a loop and the right results for 0, 1, and 8. We also need the student to explain one update.”

[Show the embedded live leaderboard. Open teacher review in a separate tab and enter the server teacher key. Review the earliest fully correct submission, ask the student to explain one state update, and click “Confirm explanation”. The automatic tests cover n=0, 1, 2, 8, and 20. Give the reward after TA confirmation.]

“Thank you. Let's do one final check together.”

## Slide 9 — Final check (14–15 minutes)

“What should `fibonacci(1)` return? Take a moment. Why?”

[Ask all students for an answer, then reveal it.]

“It returns `[0]`. We need one number, and the first number is zero.

“Today we started a value, repeated a step, updated the value, and tested the result. In the next part, we'll use the same idea with a new set of starting numbers.”

## Timing guide

| Time | Activity |
|---|---|
| 0–1 min | Poll: count the loop runs |
| 1–4 min | Build and trace the expense loop |
| 4–5 min | Poll: find the reset error |
| 5–6 min | Introduce Fibonacci and the task |
| 6–11 min | Students code on their own |
| 11–13 min | Student explanation and update error |
| 13–14 min | Check submissions and give the reward |
| 14–15 min | Check `n = 1` and close |

Students scan the QR code shown on each poll slide and vote on their phones. Each question uses its own Mentimeter presentation and QR link, so the official embedded results open on the correct question without synchronizing two slide decks. Ask students to scan the new QR code for poll 2. Keep participation enabled and the first question selected in each Menti. Before class, verify both links and preview the lesson. Students can also use the “Open voting page” link. Results are supplied by Mentimeter; there are no local vote counters.

Before class, follow FIBOLAB.md to start the backend and configure its API URL. Confirm that a student device can register and submit, and that the embedded board updates. The student QR follows the actual lesson URL automatically, including a temporary demo URL. If the service is offline, FiboLab explicitly reports it and does not fabricate scores.
