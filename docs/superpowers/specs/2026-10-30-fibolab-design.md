# FiboLab integration

User-approved scope: reuse the classmate's FiboLab UI in the slide repository; name-only student registration; actual Python execution; match fibonacci(n) returning the first n terms; rank by earliest fully correct submission; teachers can inspect and confirm submissions. Existing Mentimeter polls remain.

Static student UI lives at lab/. Slides link to it with a QR and embed its read-only teacher view. A standalone Python HTTP service with SQLite stores students, attempts and immutable first-success timestamps. Students receive opaque browser-persisted tokens, without passwords or strict invitations. Teacher-only code inspection and confirmation use a server-configured admin token. Public standings show names and submission outcomes, never code or tokens.

Student Python runs in disposable Docker containers with no network, read-only filesystem, non-root UID, resource limits and a wall timeout. Python AST checks allow this lesson's small function language and reject imports, recursion and nonessential calls. Actual output checks cover n=0,1,2,8,20; scoring is correctness 40 plus loop implementation 10, with TA explanation confirmation separate. No automatic complexity/readability claims.

Deploy service on a student-accessible Linux host with Python 3.11+ and Docker. HTTPS reverse proxy is required for a separately hosted HTTPS frontend. Configure API base and allowed origin; same-origin serving is also supported. No campus deployment credentials or destination have been supplied, so prepare and test deployment artifacts without claiming deployment.
