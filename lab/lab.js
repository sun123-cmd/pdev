'use strict';
const $ = selector => document.querySelector(selector);
const params = new URLSearchParams(location.search);
const teacherView = params.get('view') === 'teacher';
const embedded = teacherView && params.get('embed') === '1';
const base = (window.FIBOLAB_API_BASE || '').replace(/\/$/, '');
const USER_KEY = 'pdev.fibolab.student.v1';
const DRAFT_KEY = 'pdev.fibolab.draft.v1';
let user = null;
try { user = JSON.parse(localStorage.getItem(USER_KEY) || 'null'); } catch { /* Fresh registration. */ }
if (!user || typeof user.token !== 'string' || typeof user.name !== 'string') user = null;
let teacherKey = sessionStorage.getItem('pdev.fibolab.teacher') || '';
const launchKey = new URLSearchParams(location.hash.slice(1)).get('key');
if (teacherView && !embedded && launchKey) {
  teacherKey = launchKey;
  sessionStorage.setItem('pdev.fibolab.teacher', teacherKey);
  history.replaceState(null, '', location.pathname + location.search);
}
let students = [];
let selectedStudent = null;
let refreshing = false;
let submitting = false;
let lastRefresh = null;
if (teacherView) document.body.classList.add('teacher-view');
if (embedded) document.body.classList.add('embedded');
$('#teacherControls').hidden = !teacherView || embedded;
$('#teacherLink').hidden = teacherView;

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function feedback(message) { $('#feedback').textContent = message; }
function persistUser() {
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  else localStorage.removeItem(USER_KEY);
}
function profile() {
  $('#registration').hidden = !!user || teacherView;
  $('#profileName').textContent = user ? user.name : 'Not registered';
  $('#avatar').textContent = user ? user.name.slice(0, 1).toUpperCase() : '?';
  $('#changeName').hidden = !user || teacherView;
}
async function api(path, {data, token, signal} = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), data?.code ? 20000 : 12000);
  try {
    const response = await fetch(base + path, {
      method: data === undefined ? 'GET' : 'POST', cache: 'no-store', signal: signal || controller.signal,
      headers: {...(data === undefined ? {} : {'Content-Type':'application/json'}), ...(token ? {'Authorization':'Bearer ' + token} : {})},
      ...(data === undefined ? {} : {body:JSON.stringify(data)}),
    });
    if (!(response.headers.get('Content-Type') || '').includes('application/json')) {
      throw new Error('The class API is not configured here. Ask the TA to check lab/config.js.');
    }
    const result = await response.json();
    if (!response.ok) {
      const error = new Error(result.error || 'The service could not complete this request.');
      error.status = response.status;
      throw error;
    }
    return result;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The class service did not respond in time. Please retry.');
    throw error;
  } finally { clearTimeout(timeout); }
}
function time(value) { return value ? new Date(value).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'}) : '—'; }
function board() {
  $('#submissionCount').textContent = students.length;
  $('#submissionLabel').textContent = students.length === 1 ? 'student submitted' : 'students submitted';
  $('#boardCount').textContent = students.length + (students.length === 1 ? ' student' : ' students');
  const list = $('#leaderboardList');
  list.replaceChildren();
  if (!students.length) list.append(element('p', 'No submissions yet. Join the class and submit your code.', 'empty'));
  students.forEach(student => {
    const row = element('div', undefined, 'rank-row');
    row.append(element('span', student.rank ? String(student.rank).padStart(2,'0') : '—', 'rank' + (student.rank ? ' top' : '')));
    const person = element('div', undefined, 'student');
    person.append(element('span', student.name.slice(0, 2).toUpperCase(), 'mini'));
    const description = element('div');
    const status = student.latestStatus === 'running' ? 'Judging…' : student.latestStatus === 'error' ? 'Judge interrupted · please resubmit' : student.verifiedAt ? 'TA verified' : student.passed ? 'Passed · awaiting explanation' : 'Needs revision';
    description.append(element('b', student.name), element('em', status));
    description.append(element('em', `${student.attempts} attempt${student.attempts === 1 ? '' : 's'} · ${student.passed ? 'first pass ' + time(student.firstPassedAt) : 'last submit ' + time(student.lastSubmittedAt)}`));
    if (student.passed && !student.latestPassed && student.latestStatus === 'judged') description.append(element('em', 'Latest retry needs revision; first pass retained.'));
    person.append(description); row.append(person, element('span', student.score + '/50', 'points'));
    if (teacherView && !embedded && teacherKey) {
      const review = element('button', 'Review', 'ghost');
      review.setAttribute('aria-label', 'Review ' + student.name);
      review.addEventListener('click', () => reviewStudent(student.id));
      row.append(review);
    }
    list.append(row);
  });
}
async function loadBoard() {
  if (refreshing) return;
  refreshing = true;
  try {
    const result = await api('/api/standings');
    students = result.students;
    board();
    lastRefresh = Date.now();
    $('#connection').classList.remove('offline');
    $('#connection').textContent = 'Class service connected · updated ' + time(lastRefresh);
  } catch (error) {
    $('#connection').classList.add('offline');
    $('#connection').textContent = 'Offline' + (lastRefresh ? ' · showing results from ' + time(lastRefresh) : '') + ' — ' + error.message;
    if (!lastRefresh) $('#leaderboardList').replaceChildren(element('p', 'Live submissions will appear once the class service is available.', 'empty'));
  } finally { refreshing = false; }
}
function renderResult(result) {
  $('#scoreValue').replaceChildren(document.createTextNode(result.score + ' '), element('small', '/ 50'));
  $('#submissionStatus').textContent = result.passed ? 'Passed' : 'Needs revision';
  $('#submissionStatus').style.color = result.passed ? 'var(--lime)' : 'var(--red)';
  feedback(result.feedback);
  $('#testList').replaceChildren();
  (result.tests || []).forEach(test => {
    const row = element('div', undefined, 'test-row');
    row.append(element('span', test.passed ? '✓' : '×', 'check' + (test.passed ? '' : ' fail')));
    const details = element('div');
    details.append(element('div', `n=${test.input} · ${test.passed ? 'PASS' : 'CHECK'}`));
    details.append(element('div', 'Expected: ' + JSON.stringify(test.expected), 'test-meta'));
    details.append(element('div', test.error || 'Returned: ' + JSON.stringify(test.actual), 'test-meta'));
    row.append(details); $('#testList').append(row);
  });
}
$('#registerForm').addEventListener('submit', async event => {
  event.preventDefault();
  const button = event.submitter; button.disabled = true;
  try {
    user = await api('/api/students', {data:{name:$('#nameInput').value.trim()}});
    persistUser(); profile(); feedback('Registered. Write your function, then submit.');
  } catch (error) { feedback(error.message); $('#connection').textContent = error.message; }
  finally { button.disabled = false; }
});
$('#changeName').addEventListener('click', () => { user = null; persistUser(); profile(); $('#nameInput').focus(); });
$('#codeEditor').value = localStorage.getItem(DRAFT_KEY) ?? $('#codeEditor').value;
$('#codeEditor').addEventListener('input', () => localStorage.setItem(DRAFT_KEY, $('#codeEditor').value));
$('#codeEditor').addEventListener('keydown', event => {
  if (event.key === 'Tab') {
    event.preventDefault();
    const editor = event.target;
    const start = editor.selectionStart;
    editor.setRangeText('    ', start, editor.selectionEnd, 'end');
    editor.dispatchEvent(new Event('input'));
  }
});
$('#submitBtn').addEventListener('click', async () => {
  if (!user) { $('#nameInput').focus(); feedback('Join the class with your name before submitting.'); return; }
  if (submitting) return;
  submitting = true; const button = $('#submitBtn'); button.disabled = true; button.textContent = 'Running Python…';
  try {
    const result = await api('/api/submissions', {data:{code:$('#codeEditor').value}, token:user.token});
    renderResult(result); await loadBoard();
  } catch (error) {
    feedback(error.message);
    if (error.status === 401) { user = null; persistUser(); profile(); }
  } finally { submitting = false; button.disabled = false; button.textContent = 'Submit and run tests'; }
});
function lockReview() {
  teacherKey = ''; sessionStorage.removeItem('pdev.fibolab.teacher');
  $('#teacherKey').value = ''; $('#lockTeacher').hidden = true;
  $('#reviewPanel').hidden = true; board();
}
$('#teacherForm').addEventListener('submit', async event => {
  event.preventDefault();
  teacherKey = $('#teacherKey').value.trim();
  // Validate against a protected endpoint, even when there are no students yet.
  try {
    await api('/api/teacher/students/' + (students[0]?.id || 'not-yet-registered'), {token:teacherKey});
  } catch (error) {
    if (error.status !== 404) { lockReview(); $('#teacherMessage').textContent = error.message; return; }
  }
  sessionStorage.setItem('pdev.fibolab.teacher', teacherKey);
  $('#teacherKey').value = ''; $('#lockTeacher').hidden = false;
  $('#teacherMessage').textContent = 'Review unlocked for this tab. Select a student to inspect the code and confirm their explanation.';
  board();
});
$('#lockTeacher').addEventListener('click', lockReview);
async function reviewStudent(id) {
  try {
    const details = await api('/api/teacher/students/' + id, {token:teacherKey});
    selectedStudent = id;
    $('#reviewName').textContent = details.name + ' · submission history';
    const content = $('#reviewContent'); content.replaceChildren();
    details.attempts.forEach(attempt => {
      const item = element('details');
      item.open = attempt.id === details.firstPassedAttemptId || details.attempts.length === 1;
      item.append(element('summary', `${time(attempt.createdAt)} · ${attempt.result.score ?? '—'}/50 · ${attempt.status === 'running' ? 'judging' : attempt.result.passed ? 'passed' : 'needs revision'}${attempt.id === details.firstPassedAttemptId ? ' · first full pass' : ''}`));
      item.append(element('pre', attempt.code), element('p', attempt.result.feedback || 'Judging in progress. Open review again after it finishes.', 'sub'));
      content.append(item);
    });
    const verified = students.find(student => student.id === id)?.verifiedAt;
    $('#verifyBtn').disabled = !details.firstPassedAttemptId || !!verified;
    $('#reviewMessage').textContent = verified ? 'Explanation already confirmed.' : 'Ask the student to explain a loop iteration before confirming.';
    $('#reviewPanel').hidden = false;
  } catch (error) { $('#teacherMessage').textContent = error.message; }
}
$('#verifyBtn').addEventListener('click', async () => {
  $('#verifyBtn').disabled = true;
  try {
    await api('/api/teacher/verify', {data:{studentId:selectedStudent}, token:teacherKey});
    $('#reviewMessage').textContent = 'Explanation confirmed.'; await loadBoard();
  } catch (error) { $('#reviewMessage').textContent = error.message; $('#verifyBtn').disabled = false; }
});
if (teacherKey) {
  $('#lockTeacher').hidden = false;
  $('#teacherMessage').textContent = 'Review unlocked for this tab. Select a student to inspect their code.';
}
profile(); loadBoard();
setInterval(loadBoard, 5000);
document.addEventListener('visibilitychange', () => { if (!document.hidden) loadBoard(); });
