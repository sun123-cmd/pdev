# FiboLab integration

User-approved scope: reuse the classmate's FiboLab UI in the slide repository; name-only student registration; actual Python execution; match fibonacci(n) returning the first n terms; rank by earliest fully correct submission; teachers can inspect and confirm submissions. Existing Mentimeter polls remain.

Static student UI lives at lab/. Slides link to it with a QR and embed its read-only teacher view. A standalone Python HTTP service with SQLite stores students, attempts and immutable first-success timestamps. Students receive opaque browser-persisted tokens, without passwords or strict invitations. Teacher-only code inspection and confirmation use a server-configured admin token. Public standings show names and submission outcomes, never code or tokens.

Student Python runs in disposable Docker containers with no network, read-only filesystem, non-root UID, resource limits and a wall timeout. Python AST checks allow this lesson's small function language and reject imports, recursion and nonessential calls. Actual output checks cover n=0,1,2,8,20; scoring is correctness 40 plus loop implementation 10, with TA explanation confirmation separate. No automatic complexity/readability claims.

Deploy service on a student-accessible Linux host with Python 3.11+ and Docker. HTTPS reverse proxy is required for a separately hosted HTTPS frontend. Configure API base and allowed origin; same-origin serving is also supported. No campus deployment credentials or destination have been supplied, so prepare and test deployment artifacts without claiming deployment.

## Temporary demo delivery (user follow-up)

The 2026-11-03 classroom demo must require only opening links. The current user's Mac has an existing factlab-dev0-out SSH alias. A Mac .command launcher transfers authored source and starts a per-user supervisor; no administrator service installation or GPU allocation. The lab has working Bubblewrap/prlimit and Python 3.9 but no Docker daemon. Use a separately isolated Bubblewrap runner there, retaining Docker for other deployments. Empty environment, no home mount, independent network/PID namespaces, bounded virtual memory/CPU/wall time.

Start generates a temporary Cloudflare HTTPS URL, opens a fragment-key teacher link and slides, and generates the student QR from the actual origin. LAN mode selects direct LAN links even when a public-tunnel session already exists. Teacher fragment is removed immediately and never included in the student QR or public session metadata. Stop and the default four-hour deadline drain bounded in-flight graders, close the HTTP listener and stop the tunnel. Keep authored files and student data only; no automatic launch scheduled for November 3. Current-network rehearsal does not establish reachability on the eventual stage Wi-Fi.
