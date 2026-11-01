const challengeFlags = [
  'PEN-TEST{ESCAPE_YOUR_FATE}',
  'PEN-TEST{BUILD_LEARN_GROW}',
  'PEN-TEST{HACK_CLUB_TEAM}'
];

const storageKey = 'pen-test-demo-ctf';
const bankKey = 'pen-test-demo-bank';

function readProgress() {
  try {
    const raw = JSON.parse(localStorage.getItem(storageKey) || '[]');
    return Array.isArray(raw) ? raw : [];
  } catch {
    return [];
  }
}

function updateChallengeUI() {
  const unlocked = new Set(readProgress());
  const items = document.querySelectorAll('#challenge-flags .flag-item');

  items.forEach((item, index) => {
    const flag = challengeFlags[index];
    if (unlocked.has(flag)) {
      item.classList.remove('locked');
      item.classList.add('unlocked');
      item.textContent = `Flag ${index + 1}: ${flag}`;
    } else {
      item.classList.add('locked');
      item.classList.remove('unlocked');
      item.textContent = `Flag ${index + 1}: Locked`;
    }
  });

  const totalUnlocked = unlocked.size;
  const bank = totalUnlocked * 50;
  const flagBank = document.getElementById('flag-bank');
  if (flagBank) {
    flagBank.textContent = `${bank} FLAG`;
  }

  const status = document.getElementById('ctf-status');
  if (status) {
    status.textContent = `${totalUnlocked}/${challengeFlags.length} flags unlocked`;
    status.style.color = totalUnlocked === challengeFlags.length ? '#b7f34a' : '#999';
    if (totalUnlocked === challengeFlags.length) {
      status.textContent = `Room complete — ${bank} FLAG earned!`;
    }
  }

  localStorage.setItem(bankKey, String(bank));
}

document.getElementById('ctf-form')?.addEventListener('submit', function (event) {
  event.preventDefault();
  const input = document.getElementById('ctf-input');
  const guess = (input?.value || '').trim();
  const current = new Set(readProgress());
  const matched = challengeFlags.find(flag => flag.toUpperCase() === guess.toUpperCase());

  if (matched) {
    current.add(matched);
    localStorage.setItem(storageKey, JSON.stringify([...current]));
    input.value = '';
    input.placeholder = 'Flag unlocked';
    updateChallengeUI();
  } else {
    const status = document.getElementById('ctf-status');
    if (status) {
      status.textContent = 'Incorrect flag — try again.';
      status.style.color = '#ff3030';
    }
  }
});

updateChallengeUI();
