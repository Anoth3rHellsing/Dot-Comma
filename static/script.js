document.addEventListener("DOMContentLoaded", async () => {
    // Start clock
    setInterval(updateClock, 1000);
    // Check notifications every 15 seconds
    setInterval(checkNotifications, 15000);
    // Schedule routine reminders (water, breaks, meds) app-wide, regardless of screen
    initReminders();

    // Boot Animation Sequence
    const bootLines = [
        "Initializing A.N.O.T.H.E.R. System...",
        "BIOS Date 04/01/89 19:30:24 Ver 1.00",
        "CPU: Mainframe Processing Unit @ 4.77 MHz",
        "Memory check: 640K OK",
        "Loading kernel...",
        "Mounting /dev/sda1...",
        "Loading modules: S.P.R.I.N.T., TASKS, ROUTINES...",
        "Establishing neural link with Dot...",
        "READY."
    ];

    const bootContainer = document.getElementById('boot-text-container');

    const playBootAnimation = async () => {
        for (let i = 0; i < bootLines.length; i++) {
            const p = document.createElement('p');
            p.innerText = bootLines[i];
            p.style.margin = "5px 0";
            if (bootContainer) bootContainer.appendChild(p);
            await new Promise(r => setTimeout(r, Math.random() * 200 + 100));
        }
        await new Promise(r => setTimeout(r, 500));
        const bootScreen = document.getElementById('boot-screen');
        if (bootScreen) bootScreen.classList.add('hidden');
        await loadDashboard();
    };

    if (bootContainer) {
        playBootAnimation();
    } else {
        const bootScreen = document.getElementById('boot-screen');
        if (bootScreen) bootScreen.classList.add('hidden');
        await loadDashboard();
    }

    // Keyboard navigation mapping
    document.addEventListener('keydown', (e) => {
        if (!document.getElementById('main-menu').classList.contains('hidden')) {
            if (e.key === '1') navigate('sprints');
            if (e.key === '2') navigate('tasks');
            if (e.key === '3') navigate('routines');
            if (e.key === '4') navigate('dot-chat');
            if (e.key === '5') navigate('settings');
            if (e.key === '6') navigate('finance');
            if (e.key === '7') navigate('calendar');
            if (e.key === '8') navigate('jira');
        } else {
            // Only allow 0 to go back if we are not on intro screen
            if (e.key === '0' && document.getElementById('intro-screen').classList.contains('hidden')) {
                navigate('main-menu');
            }
        }
    });
});

async function loadDashboard() {
    const res = await fetch('/api/dashboard');
    const data = await res.json();

    if (data.first_run) {
        document.getElementById('intro-screen').classList.remove('hidden');
        return;
    }

    // Populate dashboard stats
    document.getElementById('motd-text').innerText = data.motd;

    const t = data.stats.tasks;
    document.getElementById('task-text').innerText = `${t.completed}/${t.total}`;
    const tPerc = t.total > 0 ? (t.completed / t.total) * 100 : 0;
    document.getElementById('task-progress').style.width = `${tPerc}%`;

    const r = data.stats.routines;
    document.getElementById('routine-text').innerText = `${r.completed}/${r.total}`;
    const rPerc = r.total > 0 ? (r.completed / r.total) * 100 : 0;
    document.getElementById('routine-progress').style.width = `${rPerc}%`;

    document.getElementById('sprint-text').innerText = data.stats.sprint_count;

    if (data.tamagotchi) {
        document.getElementById('dash-tama-hp').innerText = data.tamagotchi.health;
        document.getElementById('dash-tama-happy').innerText = data.tamagotchi.happiness;
        document.getElementById('dash-tama-clean').innerText = data.tamagotchi.cleanliness;

        const miniCat = document.getElementById('mini-cat-ascii');
        if (miniCat) {
            miniCat.style.color = colorVar(data.tamagotchi.color);
            if (data.pet_state) miniCat.innerText = catArt(data.pet_state.mood);
        }
    }

    document.getElementById('main-menu').classList.remove('hidden');
}

async function finishIntro() {
    const nameInput = document.getElementById('intro-username').value || 'User';
    await fetch('/api/finish_intro', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_name: nameInput })
    });
    // Onboarding click is a user gesture — a good moment to ask for notification permission
    requestNotificationPermission();
    document.getElementById('intro-screen').classList.add('hidden');
    await loadDashboard();
    initReminders();
}

function navigate(section) {
    // Hide all sections and main menu
    document.getElementById('main-menu').classList.add('hidden');
    document.querySelectorAll('.section').forEach(el => el.classList.add('hidden'));

    // Show requested section
    if (section === 'main-menu') {
        loadDashboard(); // Refresh stats when returning to main menu
    } else {
        document.getElementById(`${section}-section`).classList.remove('hidden');
        if (section === 'sprints') {
            loadSprints();
        } else if (section === 'settings') {
            loadSettings();
        } else if (section === 'calendar') {
            loadCalendar();
        } else if (section === 'tasks') {
            loadTasks();
        } else if (section === 'routines') {
            loadRoutines();
        } else if (section === 'dot-chat') {
            loadGeneralChat();
        } else if (section === 'finance') {
            loadFinance();
        } else if (section === 'jira') {
            loadJira();
        }
    }
}

function showNotification(msg) {
    const toast = document.getElementById('notification-toast');
    if (!toast) return;
    toast.innerText = "[DOT]: " + msg;
    toast.classList.remove('hidden');
    toast.style.opacity = 1;
    setTimeout(() => {
        toast.style.opacity = 0;
        setTimeout(() => toast.classList.add('hidden'), 500);
    }, 5000);
}

// --- System (desktop) notifications ---
function requestNotificationPermission() {
    if (!('Notification' in window)) return;
    if (Notification.permission === 'default') {
        Notification.requestPermission().catch(() => {});
    }
}

// Show a real OS notification when allowed; otherwise fall back to the in-page toast.
function systemNotify(title, body) {
    if (('Notification' in window) && Notification.permission === 'granted') {
        try {
            new Notification(title, { body });
            return;
        } catch (e) { /* fall through to the toast */ }
    }
    showNotification(`${title} — ${body}`);
}

// --- Routine reminders (water, breaks, medication, etc.) ---
let routineReminderTimers = {};

function clearRoutineReminders() {
    Object.values(routineReminderTimers).forEach(clearInterval);
    routineReminderTimers = {};
}

function scheduleRoutineReminders(routines) {
    clearRoutineReminders();
    (routines || []).forEach(r => {
        const mins = r.reminder_interval || 0;
        if (mins > 0 && !r.done_today) {
            routineReminderTimers[r.id] = setInterval(() => {
                const verb = r.category === 'medication' ? '💊 Time for' : '💧 Routine reminder';
                systemNotify(`${verb}: ${r.title}`, r.description || "Dot says: take care of this now.");
            }, mins * 60 * 1000);
        }
    });
}

async function initReminders() {
    try {
        const res = await fetch('/api/routines');
        const data = await res.json();
        scheduleRoutineReminders(data.routines || []);
    } catch (e) {
        console.error('Reminder init failed:', e);
    }
}

document.getElementById('enable-alerts-btn')?.addEventListener('click', () => {
    if (!('Notification' in window)) {
        showNotification('This browser does not support desktop notifications.');
        return;
    }
    Notification.requestPermission().then(perm => {
        if (perm === 'granted') {
            systemNotify('Desktop alerts enabled', "Dot's got your back. Hydrate or diedrate.");
        } else {
            showNotification('Desktop alerts blocked. Enable them in your browser settings.');
        }
    }).catch(() => {});
});

// --- Tamagotchi rendering helpers ---
function catArt(mood) {
    let face = '( o.o )';
    if (mood === 'happy') face = '( ^.^ )';
    else if (mood === 'struggling') face = '( ;_; )';
    return ` /\\_/\\\n${face}\n > ^ < `;
}

function colorVar(color) {
    const known = ['gold', 'cyan', 'magenta', 'green', 'red', 'blue'];
    return known.includes(color) ? `var(--corp-${color})` : 'var(--corp-gold)';
}

async function loadRoutines() {
    const res = await fetch('/api/routines');
    const data = await res.json();

    const tama = data.tamagotchi || {};
    const state = data.pet_state || {};

    document.getElementById('tama-hp').innerText = tama.health ?? 100;
    document.getElementById('tama-happy').innerText = tama.happiness ?? 100;
    document.getElementById('tama-clean').innerText = tama.cleanliness ?? 100;

    const catEl = document.getElementById('cat-ascii');
    if (catEl) {
        catEl.innerText = catArt(state.mood);
        catEl.style.color = colorVar(tama.color);
    }
    document.getElementById('pet-state-msg').innerText = state.message || '';

    const list = document.getElementById('routine-list');
    list.innerHTML = '';

    data.routines.forEach(r => {
        const li = document.createElement('li');
        li.style.marginBottom = '10px';

        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.checked = r.done_today;
        cb.disabled = r.done_today;
        if (!r.done_today) {
            cb.onchange = () => completeRoutine(r.id);
        }

        const span = document.createElement('span');
        const tag = r.category === 'medication' ? '💊 ' : '';
        const reminder = r.reminder_interval > 0 ? ` ⏰ every ${r.reminder_interval}m` : '';
        span.innerText = ` ${tag}${r.title}${reminder}`;
        if (r.category === 'medication') span.style.color = 'var(--corp-magenta)';
        if (r.done_today) {
            span.style.textDecoration = 'line-through';
            span.style.opacity = 0.5;
        }

        li.appendChild(cb);
        li.appendChild(span);
        list.appendChild(li);
    });

    // keep desktop reminders in sync with the current routine list
    scheduleRoutineReminders(data.routines);
}

document.getElementById('recolor-btn')?.addEventListener('click', async () => {
    await fetch('/api/tamagotchi/color', { method: 'POST' });
    loadRoutines();
});

async function completeRoutine(id) {
    const res = await fetch('/api/routines', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
    });
    const result = await res.json();
    if(result.dot_message) {
        document.getElementById('routine-dot-msg').innerText = result.dot_message;
    }
    loadRoutines();
}

document.getElementById('new-routine-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = document.getElementById('new-routine-title').value;
    const category = document.getElementById('new-routine-category').value;
    const reminder_interval = parseInt(document.getElementById('new-routine-interval').value) || 0;
    await fetch('/api/routines', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, category, reminder_interval })
    });
    document.getElementById('new-routine-title').value = '';
    document.getElementById('new-routine-interval').value = 0;
    loadRoutines();
});

let currentTask = null;
let timerInterval = null;
let secondsFocused = 0;

async function loadTasks() {
    const res = await fetch('/api/tasks');
    const tasks = await res.json();
    const list = document.getElementById('task-list');
    list.innerHTML = '';

    tasks.forEach(t => {
        if (t.status === 'done') return;
        const li = document.createElement('li');
        li.innerText = t.jira_key ? `> [${t.jira_key}] ${t.title}` : `> ${t.title}`;
        li.onclick = () => selectTask(t);
        list.appendChild(li);
    });
}

function selectTask(task) {
    currentTask = task;
    document.getElementById('detail-title').innerText = task.title;
    document.getElementById('detail-desc').innerText = task.description || 'No description.';
    document.getElementById('focus-btn').classList.remove('hidden');
    document.getElementById('complete-btn').classList.remove('hidden');
    document.getElementById('subtask-area').classList.remove('hidden');
    loadSubtasks(task.id);
}

async function loadSubtasks(taskId) {
    const res = await fetch(`/api/tasks/subtasks?task_id=${taskId}`);
    const subs = await res.json();
    renderSubtasks(subs);
}

function renderSubtasks(subs) {
    const list = document.getElementById('subtask-list');
    list.innerHTML = '';
    subs.forEach(s => {
        const li = document.createElement('li');
        li.style.marginBottom = '4px';

        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.checked = !!s.done;
        cb.onchange = () => toggleSubtask(s.id, cb.checked);

        const span = document.createElement('span');
        span.innerText = ' ' + s.title;
        if (s.done) {
            span.style.textDecoration = 'line-through';
            span.style.opacity = 0.5;
        }

        li.appendChild(cb);
        li.appendChild(span);
        list.appendChild(li);
    });
}

async function toggleSubtask(id, done) {
    await fetch('/api/tasks/subtasks', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, done })
    });
}

document.getElementById('deconstruct-btn')?.addEventListener('click', async () => {
    if (!currentTask) return;
    const btn = document.getElementById('deconstruct-btn');
    const original = btn.innerText;
    btn.innerText = 'Dot is breaking it down...';
    btn.disabled = true;

    const res = await fetch('/api/tasks/deconstruct', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: currentTask.id })
    });
    const result = await res.json();

    btn.innerText = original;
    btn.disabled = false;

    if (result.status === 'success') {
        renderSubtasks(result.subtasks);
    } else {
        showNotification(result.message || 'Could not deconstruct task.');
    }
});

document.getElementById('new-task-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
        title: document.getElementById('new-task-title').value,
        description: document.getElementById('new-task-desc').value
    };
    const res = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    const result = await res.json();
    if(result.dot_message) showNotification(result.dot_message);
    document.getElementById('new-task-title').value = '';
    document.getElementById('new-task-desc').value = '';
    loadTasks();
});

document.getElementById('complete-btn')?.addEventListener('click', async () => {
    if (!currentTask) return;
    await fetch('/api/tasks', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: currentTask.id, status: 'done' })
    });
    document.getElementById('detail-title').innerText = 'Select a Task';
    document.getElementById('detail-desc').innerText = '...';
    document.getElementById('focus-btn').classList.add('hidden');
    document.getElementById('complete-btn').classList.add('hidden');
    document.getElementById('subtask-area').classList.add('hidden');
    currentTask = null;
    loadTasks();
});

document.getElementById('focus-btn')?.addEventListener('click', () => {
    document.getElementById('task-list-container').style.display = 'none';
    document.getElementById('focus-ui').classList.remove('hidden');
    document.getElementById('focus-btn').classList.add('hidden');
    startTimer();
    startNudges();
});

document.getElementById('exit-focus-btn')?.addEventListener('click', () => {
    document.getElementById('task-list-container').style.display = 'block';
    document.getElementById('focus-ui').classList.add('hidden');
    document.getElementById('focus-btn').classList.remove('hidden');
    stopTimer();
    stopNudges();
});

// Every 15 minutes of focus, Dot sends a motivational nudge.
let nudgeInterval = null;
const NUDGE_MS = 15 * 60 * 1000;

function startNudges() {
    stopNudges();
    nudgeInterval = setInterval(async () => {
        try {
            const res = await fetch('/api/focus/nudge', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task: currentTask?.title })
            });
            const result = await res.json();
            if (result.message) appendChat('[DOT]: ' + result.message, '#00aaff');
        } catch (e) {
            console.error('Nudge failed:', e);
        }
    }, NUDGE_MS);
}

function stopNudges() {
    if (nudgeInterval) {
        clearInterval(nudgeInterval);
        nudgeInterval = null;
    }
}

function startTimer() {
    secondsFocused = 0;
    updateChrono();
    timerInterval = setInterval(() => {
        secondsFocused++;
        updateChrono();
    }, 1000);
}

function stopTimer() {
    clearInterval(timerInterval);
}

function updateChrono() {
    const m = Math.floor(secondsFocused / 60).toString().padStart(2, '0');
    const s = (secondsFocused % 60).toString().padStart(2, '0');
    document.getElementById('chronometer').innerText = `${m}:${s}`;
}

document.getElementById('chat-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    const msg = input.value;
    if (!msg) return;

    appendChat("YOU: " + msg);
    input.value = '';

    const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, context: currentTask?.title })
    });
    const result = await res.json();
    appendChat("[DOT]: " + result.response, "#00ff00");
});

function appendChat(text, color="#fff") {
    const box = document.getElementById('chat-box');
    const div = document.createElement('div');
    div.style.color = color;
    div.style.marginBottom = '10px';
    div.innerText = text;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
}

async function loadSettings() {
    const res = await fetch('/api/settings');
    const data = await res.json();
    document.getElementById('deepseek-key').value = data.deepseek_key || '';
    document.getElementById('context-size').value = data.context_size || 10;

    loadMemory();
    loadJiraSettings();
}

async function loadJiraSettings() {
    const res = await fetch('/api/jira/settings');
    const data = await res.json();
    document.getElementById('jira-url').value = data.jira_url || '';
    document.getElementById('jira-email').value = data.jira_email || '';
    document.getElementById('jira-auth-type').value = data.jira_auth_type || 'bearer';
    document.getElementById('jira-api-version').value = data.jira_api_version || '2';
    document.getElementById('jira-filters').value = data.jira_filters || '';
    document.getElementById('jira-tempo-url').value = data.jira_tempo_url || '';
    document.getElementById('jira-high-priority').value = data.jira_high_priority || '';
    document.getElementById('jira-poll-seconds').value = data.jira_poll_seconds || 60;
    document.getElementById('jira-token-status').innerText = data.jira_token_set ? '(token saved)' : '(no token yet)';
}

document.getElementById('jira-settings-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = {
        jira_url: document.getElementById('jira-url').value,
        jira_email: document.getElementById('jira-email').value,
        jira_token: document.getElementById('jira-token').value,
        jira_auth_type: document.getElementById('jira-auth-type').value,
        jira_api_version: document.getElementById('jira-api-version').value,
        jira_filters: document.getElementById('jira-filters').value,
        jira_tempo_url: document.getElementById('jira-tempo-url').value,
        jira_high_priority: document.getElementById('jira-high-priority').value,
        jira_poll_seconds: parseInt(document.getElementById('jira-poll-seconds').value) || 60
    };
    await fetch('/api/jira/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    document.getElementById('jira-token').value = '';
    showNotification('Jira connection saved.');
    loadJiraSettings();
});

// --- WORK (JIRA) ---
const JIRA_VIEW_LABELS = { new: 'New tickets', assigned: 'Assigned to me', waiting: 'Waiting on others', mine: 'Mine (live)' };
let jiraConfig = { high_priority_statuses: [], poll_seconds: 60, tempo_url: '', views: [] };
let jiraCurrentView = null;
let jiraCurrentIssues = [];
let jiraPollTimer = null;
let jiraSeenKeys = null; // baseline Set for new-ticket notifications

function escapeJira(s) {
    if (s == null) return '';
    const d = document.createElement('div');
    d.innerText = s;
    return d.innerHTML;
}

function jiraStatusRank(t) {
    const high = (jiraConfig.high_priority_statuses || []).map(s => s.toLowerCase());
    if (t.status && high.includes(t.status.toLowerCase())) return 0;
    if (t.status_category === 'done') return 3;
    return 1;
}

function jiraSortTickets(a, b) {
    return jiraStatusRank(a) - jiraStatusRank(b)
        || a.priority_id - b.priority_id
        || (b.updated || '').localeCompare(a.updated || '');
}

function renderJiraTabs() {
    const tabs = document.getElementById('jira-tabs');
    tabs.innerHTML = '';
    const views = (jiraConfig.views && jiraConfig.views.length) ? jiraConfig.views.slice() : [];
    views.push('mine');
    views.forEach(v => {
        const btn = document.createElement('button');
        btn.className = 'jira-tab' + (v === jiraCurrentView ? ' active' : '');
        btn.innerHTML = `${JIRA_VIEW_LABELS[v] || v} <span class="badge zero" id="jira-badge-${v}">0</span>`;
        btn.onclick = () => selectJiraView(v);
        tabs.appendChild(btn);
    });
}

async function loadJira() {
    const unconfigured = document.getElementById('jira-unconfigured');
    document.getElementById('jira-import-feedback').innerText = '';
    document.getElementById('jira-detail').innerHTML =
        '<p style="color:#888;">Select a ticket to read its description and latest replies.</p>';

    const cres = await fetch('/api/jira/config');
    jiraConfig = await cres.json();
    if (!jiraConfig.configured) {
        unconfigured.classList.remove('hidden');
        document.getElementById('jira-ticket-list').innerHTML = '';
        document.getElementById('jira-tabs').innerHTML = '';
        stopJiraPolling();
        return;
    }
    unconfigured.classList.add('hidden');

    document.getElementById('jira-sound').checked = localStorage.getItem('jiraSound') === '1';
    document.getElementById('jira-notify').checked = localStorage.getItem('jiraNotify') === '1';

    jiraCurrentView = (jiraConfig.views && jiraConfig.views.length) ? jiraConfig.views[0] : 'mine';
    renderJiraTabs();
    await selectJiraView(jiraCurrentView);
    loadJiraBoards();
    startJiraPolling();
}

async function selectJiraView(view) {
    jiraCurrentView = view;
    renderJiraTabs();
    const list = document.getElementById('jira-ticket-list');
    list.innerHTML = '<p style="color:#888;">Loading...</p>';
    const res = await fetch(`/api/jira/issues?view=${encodeURIComponent(view)}`);
    const data = await res.json();
    if (data.status !== 'success') {
        list.innerHTML = `<p style="color: var(--corp-amber);">${data.message}</p>`;
        return;
    }
    jiraCurrentIssues = data.issues;
    renderJiraTickets();
}

function renderJiraTickets() {
    const list = document.getElementById('jira-ticket-list');
    const hideClosed = document.getElementById('jira-hide-closed').checked;
    let issues = jiraCurrentIssues.slice();
    if (hideClosed) issues = issues.filter(t => jiraStatusRank(t) !== 3);
    issues.sort(jiraSortTickets);
    list.innerHTML = '';
    if (!issues.length) { list.innerHTML = '<p style="color:#888;">No tickets.</p>'; return; }
    issues.forEach(t => {
        const div = document.createElement('div');
        div.className = 'jira-ticket' + (jiraStatusRank(t) === 3 ? ' closed' : '');
        div.onclick = () => loadJiraDetail(t.key);
        div.innerHTML = `<strong style="color: var(--corp-blue);">${escapeJira(t.key)}</strong> — ${escapeJira(t.summary)}<br>
            <span style="color:#888; font-size:0.85em;">${escapeJira(t.type)} · ${escapeJira(t.status)} · <span class="prio">${escapeJira(t.priority)}</span></span>`;
        list.appendChild(div);
    });
}

document.getElementById('jira-hide-closed')?.addEventListener('change', renderJiraTickets);

async function loadJiraDetail(key) {
    const panel = document.getElementById('jira-detail');
    panel.innerHTML = 'Loading...';
    const res = await fetch(`/api/jira/issue?key=${encodeURIComponent(key)}`);
    const data = await res.json();
    if (data.status !== 'success') { panel.innerHTML = `<p style="color: var(--corp-amber);">${data.message}</p>`; return; }
    const d = data.detail;
    let html = `<div style="margin-bottom:8px;">
        <strong style="color: var(--corp-blue);">${escapeJira(d.key)}</strong> — ${escapeJira(d.summary)}<br>
        <span style="color:#888;">${escapeJira(d.status)}</span> ·
        <a href="${d.url}" target="_blank" style="color: var(--corp-gold);">Open / Reply in Jira ↗</a>
    </div>`;
    html += `<div style="border-top:1px dashed var(--corp-blue); padding-top:8px;">${d.descHtml || '<em>No description.</em>'}</div>`;
    if (d.comments && d.comments.length) {
        html += `<h4 style="color: var(--corp-teal);">Recent comments</h4>`;
        d.comments.forEach(c => {
            const when = (c.created || '').slice(0, 16).replace('T', ' ');
            html += `<div class="comment"><strong>${escapeJira(c.author)}</strong> <span style="color:#888; font-size:0.8em;">${when}</span>${c.bodyHtml}</div>`;
        });
    }
    panel.innerHTML = html;
}

async function loadJiraBoards() {
    const sel = document.getElementById('jira-board-select');
    sel.innerHTML = '<option value="">— Select a board —</option>';
    document.getElementById('jira-board-list').innerHTML = '';
    const res = await fetch('/api/jira/boards');
    const data = await res.json();
    if (data.status === 'success') {
        data.boards.forEach(b => {
            const opt = document.createElement('option');
            opt.value = b.id;
            opt.innerText = `${b.name} (${b.type})`;
            sel.appendChild(opt);
        });
    }
}

document.getElementById('jira-board-select')?.addEventListener('change', async (e) => {
    const boardId = e.target.value;
    const list = document.getElementById('jira-board-list');
    if (!boardId) { list.innerHTML = ''; return; }
    list.innerHTML = 'Loading...';
    const res = await fetch(`/api/jira/board_issues?board_id=${boardId}`);
    const data = await res.json();
    if (data.status !== 'success') { list.innerHTML = `<p style="color: var(--corp-amber);">${data.message}</p>`; return; }
    list.innerHTML = '';
    data.issues.forEach(t => {
        const div = document.createElement('div');
        div.className = 'jira-ticket';
        div.onclick = () => loadJiraDetail(t.key);
        div.innerHTML = `<strong style="color: var(--corp-blue);">${escapeJira(t.key)}</strong> — ${escapeJira(t.summary)} <span style="color:#888; font-size:0.8em;">(${escapeJira(t.status)})</span>`;
        list.appendChild(div);
    });
});

document.getElementById('jira-refresh-btn')?.addEventListener('click', () => { if (jiraCurrentView) selectJiraView(jiraCurrentView); });

document.getElementById('jira-mywork-btn')?.addEventListener('click', () => {
    if (jiraConfig.tempo_url) window.open(jiraConfig.tempo_url, '_blank');
    else showNotification('No Tempo URL configured in Settings.');
});

document.getElementById('jira-sound')?.addEventListener('change', (e) => {
    localStorage.setItem('jiraSound', e.target.checked ? '1' : '0');
    if (e.target.checked) jiraBeep(); // unlock audio on the user gesture
});

document.getElementById('jira-notify')?.addEventListener('change', (e) => {
    localStorage.setItem('jiraNotify', e.target.checked ? '1' : '0');
    if (e.target.checked) requestNotificationPermission();
});

document.getElementById('jira-import-btn')?.addEventListener('click', async () => {
    const fb = document.getElementById('jira-import-feedback');
    fb.innerText = 'Importing...';
    const res = await fetch('/api/jira/import', { method: 'POST' });
    const data = await res.json();
    fb.innerText = data.status === 'success'
        ? `Imported ${data.imported} new issue(s) into Tasks (${data.total} assigned total).`
        : (data.message || 'Import failed.');
});

// polling + new-ticket notifications + sound
function startJiraPolling() {
    stopJiraPolling();
    jiraSeenKeys = null; // first poll establishes the baseline (no notifications)
    const ms = Math.max(20, jiraConfig.poll_seconds || 60) * 1000;
    jiraPoll();
    jiraPollTimer = setInterval(jiraPoll, ms);
}

function stopJiraPolling() {
    if (jiraPollTimer) { clearInterval(jiraPollTimer); jiraPollTimer = null; }
}

async function jiraPoll() {
    const views = (jiraConfig.views && jiraConfig.views.length) ? jiraConfig.views : ['mine'];
    const currentKeys = new Set();
    const fresh = [];
    for (const v of views) {
        try {
            const res = await fetch(`/api/jira/issues?view=${encodeURIComponent(v)}`);
            const data = await res.json();
            if (data.status !== 'success') continue;
            const open = data.issues.filter(t => jiraStatusRank(t) !== 3);
            const badge = document.getElementById(`jira-badge-${v}`);
            if (badge) { badge.innerText = open.length; badge.classList.toggle('zero', open.length === 0); }
            open.forEach(t => {
                currentKeys.add(t.key);
                if (jiraSeenKeys && !jiraSeenKeys.has(t.key)) fresh.push(t);
            });
        } catch (e) { /* ignore transient poll errors */ }
    }
    if (jiraSeenKeys === null) {
        jiraSeenKeys = currentKeys;
    } else {
        fresh.forEach(t => {
            if (document.getElementById('jira-notify').checked) systemNotify(`New: ${t.key}`, t.summary || '');
            if (document.getElementById('jira-sound').checked) jiraBeep();
        });
        jiraSeenKeys = currentKeys;
    }
}

// two-tone chime via Web Audio (ported from JiraDashboard)
let _jiraAudioCtx = null;
function jiraBeep() {
    try {
        _jiraAudioCtx = _jiraAudioCtx || new (window.AudioContext || window.webkitAudioContext)();
        if (_jiraAudioCtx.state === 'suspended') _jiraAudioCtx.resume();
        const now = _jiraAudioCtx.currentTime;
        [[880, 0], [1320, 0.12]].forEach(([freq, t]) => {
            const o = _jiraAudioCtx.createOscillator(), g = _jiraAudioCtx.createGain();
            o.frequency.value = freq;
            o.connect(g); g.connect(_jiraAudioCtx.destination);
            g.gain.setValueAtTime(0.0001, now + t);
            g.gain.exponentialRampToValueAtTime(0.2, now + t + 0.02);
            g.gain.exponentialRampToValueAtTime(0.0001, now + t + 0.12);
            o.start(now + t); o.stop(now + t + 0.13);
        });
    } catch (e) { /* audio unavailable */ }
}

async function loadMemory() {
    const res = await fetch('/api/memory');
    const data = await res.json();
    const list = document.getElementById('memory-list');
    list.innerHTML = '';

    data.forEach(m => {
        const li = document.createElement('li');
        li.style.display = 'flex';
        li.style.justifyContent = 'space-between';
        li.style.marginBottom = '5px';

        li.innerHTML = `
            <span>${m.memory_text}</span>
            <button onclick="deleteMemory(${m.id})" style="padding: 0 5px; font-size: 0.8em; background-color: var(--corp-red, #800000); color: white;">X</button>
        `;
        list.appendChild(li);
    });
}

async function deleteMemory(id) {
    await fetch('/api/memory', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
    });
    loadMemory();
}

document.getElementById('memory-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = document.getElementById('new-memory').value;
    await fetch('/api/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ memory_text: text })
    });
    document.getElementById('new-memory').value = '';
    loadMemory();
});

document.getElementById('archive-chats-btn')?.addEventListener('click', async () => {
    await fetch('/api/archive_chats', { method: 'POST' });
    showNotification('All current conversations archived successfully.');
});

document.getElementById('settings-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
        deepseek_key: document.getElementById('deepseek-key').value,
        context_size: parseInt(document.getElementById('context-size').value)
    };

    await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    showNotification('Settings Saved.');
});

async function loadGeneralChat() {
    const res = await fetch('/api/general_chat');
    const history = await res.json();
    const box = document.getElementById('general-chat-box');
    box.innerHTML = '';
    history.forEach(msg => {
        appendGeneralChat(msg.sender, msg.message);
    });
}

function appendGeneralChat(sender, text) {
    const box = document.getElementById('general-chat-box');
    const div = document.createElement('div');
    if (sender === 'Dot') {
        div.className = 'message-dot';
        div.innerText = "[DOT]: " + text;
    } else {
        div.className = 'message-user';
        div.innerText = "YOU: " + text;
    }
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
}

document.getElementById('general-chat-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = document.getElementById('general-chat-input');
    const msg = input.value;
    if (!msg) return;

    appendGeneralChat('User', msg);
    input.value = '';

    const res = await fetch('/api/general_chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg })
    });
    const result = await res.json();
    if (result.status === 'success') {
        appendGeneralChat('Dot', result.response);
    }
});

// --- Finance Functions ---
async function loadFinance() {
    const res = await fetch('/api/finance');
    const data = await res.json();

    const graphContainer = document.getElementById('finance-graph');
    graphContainer.innerHTML = '';

    if (data.daily_totals && data.daily_totals.length > 0) {
        // Find max total for scaling bars
        let maxVal = 0;
        data.daily_totals.forEach(d => {
            if (d.total_spent > maxVal) maxVal = d.total_spent;
            if (d.total_won > maxVal) maxVal = d.total_won;
        });

        data.daily_totals.forEach(d => {
            const spentPct = maxVal > 0 ? (d.total_spent / maxVal) * 100 : 0;
            const wonPct = maxVal > 0 ? (d.total_won / maxVal) * 100 : 0;

            const dayRow = document.createElement('div');
            dayRow.style.marginBottom = '10px';
            dayRow.innerHTML = `
                <div style="font-size: 0.8rem; color: #aaa;">${d.date}</div>
                <div style="display: flex; gap: 5px; align-items: center; height: 15px;">
                    <span style="font-size: 0.7rem; width: 40px; text-align: right; color: #ff3333;">-${d.total_spent.toFixed(2)}</span>
                    <div style="flex: 1; display: flex; height: 100%;">
                        <div style="width: ${spentPct}%; background-color: #ff3333;"></div>
                    </div>
                </div>
                <div style="display: flex; gap: 5px; align-items: center; height: 15px;">
                    <span style="font-size: 0.7rem; width: 40px; text-align: right; color: #00ff00;">+${d.total_won.toFixed(2)}</span>
                    <div style="flex: 1; display: flex; height: 100%;">
                        <div style="width: ${wonPct}%; background-color: #00ff00;"></div>
                    </div>
                </div>
            `;
            graphContainer.appendChild(dayRow);
        });
    } else {
        graphContainer.innerHTML = '<p style="color: #aaa;">No transactions recorded.</p>';
    }
}

document.getElementById('finance-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const amount = document.getElementById('finance-amount').value;
    const desc = document.getElementById('finance-desc').value;
    const category = document.getElementById('finance-category').value;

    document.getElementById('finance-feedback').innerText = "Logging transaction...";

    const res = await fetch('/api/finance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount: parseFloat(amount), description: desc, category: category })
    });
    const result = await res.json();

    if (result.status === 'success') {
        document.getElementById('finance-feedback').innerText = "Transaction logged.";
        const chatBox = document.getElementById('finance-chat-box');
        chatBox.innerHTML += `<div style="margin-top: 10px; padding-top: 10px; border-top: 1px dashed #008080;"><strong>[DOT]:</strong> ${result.dot_message}</div>`;
        chatBox.scrollTop = chatBox.scrollHeight;
        document.getElementById('finance-form').reset();
        loadFinance();
    }
});

document.getElementById('finance-advice-btn')?.addEventListener('click', async () => {
    const chatBox = document.getElementById('finance-chat-box');
    chatBox.innerHTML += `<div style="margin-top: 10px; padding-top: 10px; border-top: 1px dashed #008080; color: #888;">Requesting financial analysis...</div>`;
    chatBox.scrollTop = chatBox.scrollHeight;

    const res = await fetch('/api/finance/advice');
    const result = await res.json();

    if (result.status === 'success') {
        chatBox.innerHTML += `<div style="margin-top: 10px; padding-top: 10px; border-top: 1px dashed #008080;"><strong>[DOT]:</strong> ${result.advice}</div>`;
        chatBox.scrollTop = chatBox.scrollHeight;
    }
});

async function loadSprints() {
    const res = await fetch('/api/sprints');
    const data = await res.json();
    const list = document.getElementById('sprints-list');
    list.innerHTML = '';

    const select = document.getElementById('scrum-sprint');
    if (select) select.innerHTML = '<option value="">— None —</option>';

    if (data.length === 0) {
        list.innerHTML = '<p style="color:#888;">No sprints yet. Create one to begin.</p>';
    }

    data.forEach(s => {
        const div = document.createElement('div');
        div.style.marginBottom = '15px';
        div.style.borderBottom = '1px dashed #008080';
        div.style.paddingBottom = '10px';

        div.innerHTML = `
            <strong>${s.objective}</strong><br>
            <small>Start: ${s.start_date} | End: ${s.end_date}</small>
            <div class="progress-bar-container" style="margin: 6px 0;">
                <div class="progress-bar teal" style="width:${s.progress}%;"></div>
            </div>
            <span>Progress: <input type="number" min="0" max="100" value="${s.progress}" id="sprint-prog-${s.id}" style="width:50px;">%</span>
            <button onclick="updateSprint(${s.id})" style="padding: 2px 5px; font-size: 0.8em;">UPDATE</button>
        `;
        list.appendChild(div);

        if (select) {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.innerText = s.objective;
            select.appendChild(opt);
        }
    });

    loadScrum();
}

async function loadScrum() {
    const res = await fetch('/api/scrum');
    const data = await res.json();

    const banner = document.getElementById('overcome-banner');
    if (banner) {
        if (data.overcome_count > 0) {
            banner.style.display = 'block';
            banner.innerText = `★ You've overcome ${data.overcome_count} impediment${data.overcome_count === 1 ? '' : 's'} so far. You made it through every single one. Keep going.`;
        } else {
            banner.style.display = 'none';
        }
    }

    const impList = document.getElementById('impediments-list');
    if (!impList) return;
    impList.innerHTML = '';

    if (!data.impediments || data.impediments.length === 0) {
        impList.innerHTML = '<p style="color:#888;">No impediments logged. Smooth sailing — for now.</p>';
        return;
    }

    const open = data.impediments.filter(i => !i.resolved);
    const done = data.impediments.filter(i => i.resolved);

    open.forEach(i => {
        const div = document.createElement('div');
        div.style.marginBottom = '8px';
        div.innerHTML = `
            <span>⚠ ${i.description}</span>
            <button onclick="resolveImpediment(${i.id})" style="float:right; padding:1px 6px; font-size:0.7em;">RESOLVED</button>
            <div style="clear:both;"></div>
        `;
        impList.appendChild(div);
    });

    done.forEach(i => {
        const div = document.createElement('div');
        div.style.marginBottom = '6px';
        div.style.opacity = 0.5;
        div.innerHTML = `<span style="text-decoration: line-through;">✓ ${i.description}</span>`;
        impList.appendChild(div);
    });
}

async function resolveImpediment(id) {
    const res = await fetch('/api/impediments/resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
    });
    const result = await res.json();
    if (result.dot_message) showNotification(result.dot_message);
    loadScrum();
}

document.getElementById('scrum-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fb = document.getElementById('scrum-feedback');
    fb.innerText = 'Dot is reviewing your stand-up...';

    const data = {
        sprint_id: document.getElementById('scrum-sprint').value || null,
        yesterday: document.getElementById('scrum-yesterday').value,
        today: document.getElementById('scrum-today').value,
        impediments: document.getElementById('scrum-impediments').value
    };

    const res = await fetch('/api/scrum', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    const result = await res.json();

    if (result.status === 'success') {
        fb.innerText = result.feedback;
        document.getElementById('scrum-yesterday').value = '';
        document.getElementById('scrum-today').value = '';
        document.getElementById('scrum-impediments').value = '';
        loadScrum();
    } else {
        fb.innerText = 'System error logging stand-up.';
    }
});

async function updateSprint(id) {
    const prog = document.getElementById(`sprint-prog-${id}`).value;
    const res = await fetch('/api/sprints', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: id, progress: parseInt(prog) })
    });
    const result = await res.json();
    if(result.status === 'success') {
        showNotification(result.feedback);
        loadSprints();
    }
}

document.getElementById('sprint-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const feedbackDiv = document.getElementById('sprint-feedback');
    feedbackDiv.innerText = "Analyzing objective... Please wait.";

    const data = {
        objective: document.getElementById('sprint-objective').value,
        start_date: document.getElementById('sprint-start').value,
        end_date: document.getElementById('sprint-end').value
    };

    const res = await fetch('/api/sprints', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    const result = await res.json();
    if (result.status === 'success') {
        feedbackDiv.innerText = result.feedback;
        document.getElementById('sprint-objective').value = '';
        document.getElementById('sprint-start').value = '';
        document.getElementById('sprint-end').value = '';
        loadSprints();
    } else {
        feedbackDiv.innerText = "System error creating sprint.";
    }
});

document.getElementById('remember-btn')?.addEventListener('click', async () => {
    const input = document.getElementById('general-chat-input');
    const msg = input.value;
    if (!msg) {
        showNotification("Type what you want me to remember in the chat box first.");
        return;
    }

    appendGeneralChat('User', msg + " (Memory Search)");
    input.value = '';

    const res = await fetch('/api/remember', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg })
    });
    const result = await res.json();
    if (result.status === 'success') {
        appendGeneralChat('Dot', result.response);
    }
});

function updateClock() {
    const clockEl = document.getElementById('clock-display');
    if (clockEl) {
        const now = new Date();
        clockEl.innerText = now.toLocaleTimeString('en-US', { hour12: false });
    }
}

async function checkNotifications() {
    try {
        const res = await fetch('/api/notifications');
        const data = await res.json();
        if (data.notifications && data.notifications.length > 0) {
            const overlay = document.getElementById('notification-overlay');
            if (!overlay) return;
            const list = document.getElementById('notification-list');
            list.innerHTML = '';
            data.notifications.forEach(n => {
                const p = document.createElement('p');
                p.innerText = `[ALERT] ${n.message}`;
                p.style.color = 'var(--corp-amber)';
                list.appendChild(p);
                systemNotify('SYSTEM ALERT', n.message);
            });
            overlay.classList.remove('hidden');
            setTimeout(() => {
                overlay.classList.add('hidden');
            }, 10000);
        }
    } catch (e) {
        console.error("Error checking notifications:", e);
    }
}

async function loadCalendar() {
    const res = await fetch('/api/calendar');
    const events = await res.json();

    const list = document.getElementById('calendar-list');
    list.innerHTML = '';

    events.forEach(e => {
        const div = document.createElement('div');
        div.style.borderBottom = "1px dotted var(--corp-blue)";
        div.style.marginBottom = "10px";
        div.innerHTML = `
            <strong>${e.title}</strong><br>
            <span style="color: #888;">${new Date(e.event_datetime).toLocaleString()}</span>
            ${e.is_scrum ? '<span style="color:var(--corp-amber)"> [Daily Scrum]</span>' : ''}
            <button onclick="deleteEvent(${e.id})" style="float: right; padding: 2px 5px; color: var(--corp-red); border-color: var(--corp-red);">X</button>
            <div style="clear:both;"></div>
        `;
        list.appendChild(div);
    });
}

document.getElementById('calendar-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = document.getElementById('calendar-title').value;
    const dt = document.getElementById('calendar-datetime').value;
    if(!title || !dt) return;

    await fetch('/api/calendar', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({title, datetime: dt})
    });

    document.getElementById('calendar-title').value = '';
    document.getElementById('calendar-datetime').value = '';
    loadCalendar();
});

async function deleteEvent(id) {
    await fetch('/api/calendar', {
        method: 'DELETE',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id})
    });
    loadCalendar();
}
