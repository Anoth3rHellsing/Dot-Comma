document.addEventListener("DOMContentLoaded", () => {
    // Simulate boot sequence
    setTimeout(() => {
        document.getElementById('boot-screen').classList.add('hidden');
        document.getElementById('main-menu').classList.remove('hidden');
    }, 2000);

    // Keyboard navigation mapping
    document.addEventListener('keydown', (e) => {
        if (!document.getElementById('main-menu').classList.contains('hidden')) {
            if (e.key === '1') navigate('scrum');
            if (e.key === '2') navigate('tasks');
            if (e.key === '3') navigate('routines');
            if (e.key === '4') navigate('settings');
        } else {
            if (e.key === '0') navigate('main-menu');
        }
    });
});

function navigate(section) {
    // Hide all sections and main menu
    document.getElementById('main-menu').classList.add('hidden');
    document.querySelectorAll('.section').forEach(el => el.classList.add('hidden'));

    // Show requested section
    if (section === 'main-menu') {
        document.getElementById('main-menu').classList.remove('hidden');
    } else {
        document.getElementById(`${section}-section`).classList.remove('hidden');
        if (section === 'settings') {
            loadSettings();
        } else if (section === 'tasks') {
            loadTasks();
        } else if (section === 'routines') {
            loadRoutines();
        }
    }
}

async function loadRoutines() {
    const res = await fetch('/api/routines');
    const data = await res.json();

    // Update tamagotchi stats
    if (data.tamagotchi) {
        document.getElementById('tama-hp').innerText = data.tamagotchi.health;
        document.getElementById('tama-happy').innerText = data.tamagotchi.happiness;
        document.getElementById('tama-clean').innerText = data.tamagotchi.cleanliness;
    }

    // Update routine list
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

// Global state for tasks
let currentTask = null;
let timerInterval = null;
let secondsFocused = 0;

async function loadTasks() {
    const res = await fetch('/api/tasks');
    const tasks = await res.json();
    const list = document.getElementById('task-list');
    list.innerHTML = '';

    tasks.forEach(t => {
        if (t.status === 'done') return; // Don't show completed tasks in list
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
    if(result.dot_message) alert(result.dot_message);
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

// Focus Mode Logic
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
    document.getElementById('openai-key').value = data.openai_key || '';
    document.getElementById('gemini-key').value = data.gemini_key || '';
    document.getElementById('deepseek-key').value = data.deepseek_key || '';
    if (data.active_provider) {
        document.getElementById('active-provider').value = data.active_provider;
    }
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
        openai_key: document.getElementById('openai-key').value,
        gemini_key: document.getElementById('gemini-key').value,
        deepseek_key: document.getElementById('deepseek-key').value,
        active_provider: document.getElementById('active-provider').value
    };

    await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    alert('Settings Saved.');
});
