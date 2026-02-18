const BLINK_J_SECONDS = 300;
const BLINK_B_SECONDS = 60;

const state = {
  soundOn: true,
  search: '',
  trains: [],
  loading: false,
};

const rowsEl = document.getElementById('trainRows');
const clockEl = document.getElementById('clock');
const runtimeStatus = document.getElementById('runtimeStatus');
const alertList = document.getElementById('alertList');
const search = document.getElementById('search');

const timeFmt = new Intl.DateTimeFormat('de-AT', {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
});

function countdown(seconds) {
  const s = Math.max(seconds, 0);
  const h = String(Math.floor(s / 3600)).padStart(2, '0');
  const m = String(Math.floor((s % 3600) / 60)).padStart(2, '0');
  const sec = String(s % 60).padStart(2, '0');
  return `${h}:${m}:${sec}`;
}

function addAlert(msg) {
  const li = document.createElement('li');
  li.textContent = `${timeFmt.format(new Date())} — ${msg}`;
  alertList.prepend(li);
  while (alertList.children.length > 14) alertList.removeChild(alertList.lastChild);
}

function beep() {
  if (!state.soundOn) return;
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return;
  const ctx = new Ctx();
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.frequency.value = 880;
  gain.gain.value = 0.05;
  osc.start();
  setTimeout(() => {
    osc.stop();
    ctx.close();
  }, 120);
}

async function fetchTrains() {
  const q = encodeURIComponent(state.search);
  const res = await fetch(`/api/trains?search=${q}`);
  if (!res.ok) throw new Error('API error');
  const data = await res.json();
  state.trains = data.trains;
  runtimeStatus.textContent = 'RUNNING';
}

async function handleArrivalCheck(check) {
  addAlert(`Zug ${check.trainNo} soll jetzt in Innsbruck sein. Bitte bestätigen.`);
  beep();

  const present = window.confirm(
    `Zug ${check.trainNo}: Ist der Zug wirklich in Innsbruck angekommen?\n\nOK = Ja\nAbbrechen = Nein (Verspätung eingeben)`
  );

  let payload = { trainId: check.id, isPresent: present };
  if (!present) {
    const value = window.prompt(`Wie viele Minuten Verspätung hat Zug ${check.trainNo}?`, '5');
    const parsed = Number.parseInt(value ?? '0', 10);
    const delayMinutes = Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
    payload = { ...payload, delayMinutes };
    addAlert(
      delayMinutes > 0
        ? `Zug ${check.trainNo} mit +${delayMinutes} Min Verspätung verschoben.`
        : `Zug ${check.trainNo} nicht bestätigt (keine Zusatz-Verspätung eingetragen).`
    );
  } else {
    addAlert(`Ankunft von Zug ${check.trainNo} in Innsbruck bestätigt.`);
  }

  await fetch('/api/arrival-confirmation', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

async function tick() {
  try {
    const res = await fetch('/api/tick', { method: 'POST' });
    if (!res.ok) return;
    const data = await res.json();

    for (const alert of data.alerts || []) {
      addAlert(`Zug ${alert.trainNo} fährt JETZT ab!`);
      beep();
    }

    for (const check of data.arrivalChecks || []) {
      await handleArrivalCheck(check);
    }
  } catch {
    runtimeStatus.textContent = 'OFFLINE';
  }
}

function render() {
  const now = new Date();
  clockEl.textContent = timeFmt.format(now);
  rowsEl.innerHTML = '';

  for (const train of state.trains) {
    const rest = train.restSeconds;
    const departed = train.departed || rest <= 0;

    const tr = document.createElement('tr');
    if (rest <= 600 && rest > 0) tr.classList.add('row-near');

    const statusClass = departed ? 'badge badge-departed' : 'badge badge-live';
    const statusLabel = departed ? 'ABGEFAHREN' : 'LIVE';

    let cdClass = 'countdown good';
    if (rest <= 600 && rest > BLINK_J_SECONDS) cdClass = 'countdown warn'; // 10-5 Min orange
    if (rest <= BLINK_J_SECONDS && rest > 0) cdClass = 'countdown danger blink-j'; // 5-1 Min rot+blink
    if (departed) cdClass = 'countdown departed';

    const trainNoClass = rest <= BLINK_B_SECONDS && rest > 0 ? 'trainno blink-b' : 'trainno'; // 1 Min bis Abfahrt

    const dep = new Date(train.departureAt);
    const ibkArrival = new Date(train.innsbruckArrivalAt);
    const arrivalClass = train.arrivalWindowActive ? 'arrival-glow' : '';

    tr.innerHTML = `
      <td>${train.route}</td>
      <td class="${trainNoClass}">${train.trainNo}</td>
      <td>${train.start}</td>
      <td class="${arrivalClass}">${timeFmt.format(ibkArrival)}</td>
      <td>${timeFmt.format(dep)}</td>
      <td><span class="${statusClass}">${statusLabel}</span></td>
      <td class="${cdClass}">${departed ? 'ABGEFAHREN' : countdown(rest)}</td>
      <td>${train.delayMinutes ? `+${train.delayMinutes} Min` : '-'}</td>
      <td>${train.note || ''}</td>
    `;
    rowsEl.appendChild(tr);
  }
}

async function refresh() {
  if (state.loading) return;
  state.loading = true;
  try {
    await tick();
    await fetchTrains();
  } catch {
    runtimeStatus.textContent = 'OFFLINE';
  } finally {
    state.loading = false;
    render();
  }
}

document.getElementById('toggleSound').addEventListener('click', (e) => {
  state.soundOn = !state.soundOn;
  e.target.textContent = `🔔 Sound: ${state.soundOn ? 'AN' : 'AUS'}`;
});

document.getElementById('addDemoTrain').addEventListener('click', async () => {
  const innsbruckArrivalAt = new Date(Date.now() + 90 * 1000).toISOString();
  const departureAt = new Date(Date.now() + 2 * 60_000).toISOString();
  const body = {
    route: 'Railjet → Vorarlberg',
    trainNo: String(Math.floor(Math.random() * 900) + 100),
    start: 'Innsbruck',
    innsbruckArrivalAt,
    departureAt,
    note: 'Dynamisch hinzugefügt',
  };

  const res = await fetch('/api/trains', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (res.ok) {
    addAlert('Neuer Demo-Zug wurde hinzugefügt.');
    await refresh();
  }
});

search.addEventListener('input', async (e) => {
  state.search = e.target.value.trim();
  await refresh();
});

setInterval(refresh, 1000);
refresh();
