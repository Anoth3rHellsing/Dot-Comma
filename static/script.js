document.addEventListener("DOMContentLoaded", async () => {
    // Simulate boot sequence
    setTimeout(async () => {
        document.getElementById('boot-screen').classList.add('hidden');
        await loadDashboard();
    }, 2000);

    // Keyboard navigation mapping
    document.addEventListener('keydown', (e) => {
        if (!document.getElementById('main-menu').classList.contains('hidden')) {
            if (e.key === '1') navigate('scrum');
            if (e.key === '2') navigate('tasks');
            if (e.key === '3') navigate('routines');
            if (e.key === '4') navigate('dot-chat');
            if (e.key === '5') navigate('settings');
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

    document.getElementById('scrum-text').innerText = data.stats.scrum_count;

    if (data.tamagotchi) {
        document.getElementById('dash-tama-hp').innerText = data.tamagotchi.health;
        document.getElementById('dash-tama-happy').innerText = data.tamagotchi.happiness;
        document.getElementById('dash-tama-clean').innerText = data.tamagotchi.cleanliness;
    }

    document.getElementById('main-menu').classList.remove('hidden');
}

async function finishIntro() {
    await fetch('/api/finish_intro', { method: 'POST' });
    document.getElementById('intro-screen').classList.add('hidden');
    await loadDashboard();
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
        if (section === 'settings') {
            loadSettings();
        } else if (section === 'tasks') {
            loadTasks();
        } else if (section === 'routines') {
            loadRoutines();
        } else if (section === 'dot-chat') {
            loadGeneralChat();
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

async function loadRoutines() {
    const res = await fetch('/api/routines');
    const data = await res.json();

    if (data.tamagotchi) {
        document.getElementById('tama-hp').innerText = data.tamagotchi.health;
        document.getElementById('tama-happy').innerText = data.tamagotchi.happiness;
        document.getElementById('tama-clean').innerText = data.tamagotchi.cleanliness;
    }

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
        span.innerText = ` ${r.title}`;
        if (r.done_today) {
            span.style.textDecoration = 'line-through';
            span.style.opacity = 0.5;
        }

        li.appendChild(cb);
        li.appendChild(span);
        list.appendChild(li);
    });
}

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
    await fetch('/api/routines', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title })
    });
    document.getElementById('new-routine-title').value = '';
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
        li.innerText = `> ${t.title}`;
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
}

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
    currentTask = null;
    loadTasks();
});

document.getElementById('focus-btn')?.addEventListener('click', () => {
    document.getElementById('task-list-container').style.display = 'none';
    document.getElementById('focus-ui').classList.remove('hidden');
    document.getElementById('focus-btn').classList.add('hidden');
    startTimer();
});

document.getElementById('exit-focus-btn')?.addEventListener('click', () => {
    document.getElementById('task-list-container').style.display = 'block';
    document.getElementById('focus-ui').classList.add('hidden');
    document.getElementById('focus-btn').classList.remove('hidden');
    stopTimer();
});

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
}

document.getElementById('scrum-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const feedbackDiv = document.getElementById('scrum-feedback');
    feedbackDiv.innerText = "Analyzing response... Analyzing excuses... Please wait.";

    const data = {
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
        feedbackDiv.innerText = result.feedback;
        document.getElementById('scrum-yesterday').value = '';
        document.getElementById('scrum-today').value = '';
        document.getElementById('scrum-impediments').value = '';
    } else {
        feedbackDiv.innerText = "System error logging scrum.";
    }
});

document.getElementById('settings-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
        deepseek_key: document.getElementById('deepseek-key').value
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
