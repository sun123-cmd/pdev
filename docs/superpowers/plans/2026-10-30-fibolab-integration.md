# FiboLab Integration Implementation Plan

> Execute inline in the current dedicated repository checkout. User approved integration and repairs on 2026-10-30.

**Goal:** Students submit Fibonacci code and teachers see real, persistent results inside the slides.

**Architecture:** Static lab frontend plus Python/SQLite API; bounded Docker judging.

**Tech Stack:** Browser JavaScript, Python 3.11+, SQLite, Docker.

**Spec:** docs/superpowers/specs/2026-10-30-fibolab-design.md

## Global Constraints

- Name-only registration; no strict invite code.
- fibonacci(n) returns the first n terms, including [] at n=0.
- Earliest fully correct submission wins; later retries never change first-success order.
- Keep Mentimeter polls and both slide entrypoints.
- Never execute submitted Python directly on the API host.

## Tasks

- [x] Write and run failing tests for real grading, wrong returns, syntax/runtime errors, loops and recursion, timeout, and preserved first-success rankings. Interfaces: runner.grade(code), Store.register(name), Store.submit(student_id, code, result), Store.standings().
- [x] Implement service/runner.py, service/grader.py and service/store.py. Run the tests against real Python outputs and persistent SQLite.
- [x] Add service/server.py registration/submission/standings/teacher endpoints, request validation, CORS and bounded concurrent judging. Exercise real HTTP requests and auth failures.
- [x] Reuse classmate's authored HTML/CSS in lab/, replace its regex-grade UI with real API results, explicit disconnected states, text-safe rendering and persistent registration/drafts. Add teacher view and confirmation.
- [x] Update index.html and lesson.html: student QR/link at slide 6, read-only standings iframe at slide 8. Update speaker script.
- [x] Add runner Dockerfile, HTTPS proxy/systemd deployment examples and Chinese runbook. Run Docker end-to-end judging, HTTP integration and browser checks for student/teacher synchronization, mobile layout, errors and existing slide interactions.
Publication follows final verification: commit, push feature branch and open a PR against upstream; provide an export ZIP. Upstream direct push is unavailable to the authenticated account.

Course label corrected to COMP 1023 in both slide entrypoints. Independent review found and reproduced a recursive alias bypass; reserved builtin names now cannot be rebound, with a regression test.

## One-click demo follow-up

- [x] Probe factlab-dev0-out: Python 3.9, working Bubblewrap/prlimit, cloudflared; Docker daemon unavailable.
- [x] Add rootless isolated grading, SSH source transfer, per-user start/stop supervisor, four-hour expiry, temporary HTTPS and LAN links.
- [x] Add Mac launchers, automatic teacher fragment login, same-origin dynamic student QR and concise Chinese show-day instructions.
- [x] Reproduce and fix review findings: LAN selection must override existing tunnel links; shutdown drains active bounded judges before exiting.
- [x] Validate all 22 tests on the real lab host, browser workflows over temporary HTTPS and local LAN, and actual expiry during infinite-loop grading.
- [x] Stop rehearsal services and archive rehearsal data. November 3 launch remains manual, not scheduled.
