// API Configuration
const API_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') 
    ? 'http://localhost:5000/api' 
    : '/api';

// State
const state = {
    isAdmin: false,
    token: null,
    username: null,
    role: null,
    groups: [],
    currentMatchId: null,
    currentGroupId: null,
    competitionName: 'EA FC 26 CHAMPIONSHIP',
    historySort: 'time', // 'time' or 'group'
    logs: []
};

// Extensive Country Code Mapping
const countryCodes = {
    'argentina': 'ar', 'france': 'fr', 'brazil': 'br', 'germany': 'de', 'spain': 'es',
    'england': 'gb-eng', 'portugal': 'pt', 'italy': 'it', 'netherlands': 'nl', 'belgium': 'be',
    'croatia': 'hr', 'uruguay': 'uy', 'usa': 'us', 'mexico': 'mx', 'japan': 'jp',
    'south korea': 'kr', 'indonesia': 'id', 'saudi arabia': 'sa', 'australia': 'au',
    'morocco': 'ma', 'colombia': 'co', 'switzerland': 'ch', 'senegal': 'sn', 'denmark': 'dk',
    'poland': 'pl', 'serbia': 'rs', 'chile': 'cl', 'wales': 'gb-wls', 'scotland': 'gb-sct',
    'sweden': 'se', 'nigeria': 'ng', 'egypt': 'eg', 'cameroon': 'cm', 'ghana': 'gh',
    'ivory coast': 'ci', 'canada': 'ca', 'ecuador': 'ec', 'peru': 'pe', 'qatar': 'qa',
    'iran': 'ir', 'iraq': 'iq', 'malaysia': 'my', 'thailand': 'th', 'vietnam': 'vn',
    'philippines': 'ph', 'singapore': 'sg', 'turkey': 'tr', 'greece': 'gr', 'ukraine': 'ua',
    'ireland': 'ie', 'norway': 'no', 'finland': 'fi', 'iceland': 'is', 'russia': 'ru',
    'china': 'cn', 'india': 'in', 'south africa': 'za', 'romania': 'ro', 'czech republic': 'cz',
    'czechia': 'cz', 'belarus': 'by', 'slovakia': 'sk', 'slovenia': 'si', 'austria': 'at', 'hungary': 'hu'
};

const getFlagUrl = (code) => {
    if (!code) return 'https://via.placeholder.com/100x66/333333/ffffff?text=FC';
    return `https://flagcdn.com/w160/${code.toLowerCase()}.png`;
};

const getCountryCode = (name) => {
    const n = name.toLowerCase().trim();
    if (countryCodes[n]) return countryCodes[n];
    for (const [key, value] of Object.entries(countryCodes)) {
        if (n.includes(key) || key.includes(n)) return value;
    }
    return null;
};

const app = {
    alertResolve: null,
    confirmResolve: null,

    showAlert(message) {
        return new Promise(resolve => {
            this.alertResolve = resolve;
            const msgEl = document.getElementById('custom-alert-message');
            if (msgEl) msgEl.innerText = message;
            const modal = document.getElementById('custom-alert-modal');
            if (modal) modal.classList.remove('hidden');
            const okBtn = document.getElementById('custom-alert-ok-btn');
            if (okBtn) setTimeout(() => okBtn.focus(), 50);
        });
    },

    closeAlert() {
        const modal = document.getElementById('custom-alert-modal');
        if (modal) modal.classList.add('hidden');
        if (this.alertResolve) {
            this.alertResolve();
            this.alertResolve = null;
        }
    },

    showConfirm(message) {
        return new Promise(resolve => {
            this.confirmResolve = resolve;
            const msgEl = document.getElementById('custom-confirm-message');
            if (msgEl) msgEl.innerText = message;
            const modal = document.getElementById('custom-confirm-modal');
            if (modal) modal.classList.remove('hidden');
        });
    },

    closeConfirm(result) {
        const modal = document.getElementById('custom-confirm-modal');
        if (modal) modal.classList.add('hidden');
        if (this.confirmResolve) {
            this.confirmResolve(result);
            this.confirmResolve = null;
        }
    },

    async init() {
        const savedTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
        const themeBtn = document.getElementById('theme-toggle-btn');
        if (themeBtn) {
            themeBtn.innerText = savedTheme === 'dark' ? '🌙' : '☀️';
        }

        this.checkLoginStatus();
        this.setupEventListeners();
        await this.fetchSettings();
        await this.fetchGroups();
        this.setupRealtimeUpdates();
    },

    checkLoginStatus() {
        const token = localStorage.getItem('adminToken');
        const username = localStorage.getItem('adminUsername');
        const role = localStorage.getItem('adminRole');

        if (token && username) {
            state.isAdmin = true;
            state.token = token;
            state.username = username;
            state.role = role || 'admin';

            document.body.classList.add('admin-mode');
            const loginBtn = document.getElementById('admin-login-btn');
            if (loginBtn) loginBtn.classList.add('hidden');

            const profileContainer = document.getElementById('admin-profile-container');
            if (profileContainer) profileContainer.classList.remove('hidden');

            const pInit = document.getElementById('profile-initial');
            if (pInit) pInit.innerText = username.charAt(0).toUpperCase();

            const pInitL = document.getElementById('profile-initial-large');
            if (pInitL) pInitL.innerText = username.charAt(0).toUpperCase();

            const dUser = document.getElementById('dropdown-username');
            if (dUser) dUser.innerText = username;

            const dRole = document.getElementById('dropdown-role');
            if (dRole) dRole.innerText = state.role;

            const compDisplay = document.getElementById('competition-name-display');
            if (compDisplay) {
                compDisplay.setAttribute('contenteditable', 'true');
                compDisplay.classList.add('editable-comp-name');
            }

            const mAdmins = document.getElementById('dropdown-manage-admins');
            const vLogs = document.getElementById('dropdown-view-logs');
            if (state.role === 'superadmin') {
                if (mAdmins) mAdmins.classList.remove('hidden');
                if (vLogs) vLogs.classList.remove('hidden');
            } else {
                if (mAdmins) mAdmins.classList.add('hidden');
                if (vLogs) vLogs.classList.add('hidden');
            }
        } else {
            this.logoutState();
            const compDisplay = document.getElementById('competition-name-display');
            if (compDisplay) {
                compDisplay.removeAttribute('contenteditable');
                compDisplay.classList.remove('editable-comp-name');
            }
        }
    },

    setupEventListeners() {
        const loginBtn = document.getElementById('admin-login-btn');
        if (loginBtn) loginBtn.addEventListener('click', () => this.openModal('login-modal'));

        window.addEventListener('click', (e) => {
            const container = document.getElementById('admin-profile-container');
            const dropdown = document.getElementById('profile-dropdown');
            if (container && dropdown && !container.contains(e.target) && !dropdown.classList.contains('hidden')) {
                dropdown.classList.add('hidden');
            }
        });

        window.addEventListener('keydown', (e) => {
            const alertModal = document.getElementById('custom-alert-modal');
            if (alertModal && !alertModal.classList.contains('hidden')) {
                if (e.key === 'Enter' || e.key === 'Escape') {
                    e.preventDefault();
                    e.stopPropagation();
                    this.closeAlert();
                }
            }
        }, true);

        const addGrpBtn = document.getElementById('add-group-btn');
        if (addGrpBtn) addGrpBtn.addEventListener('click', () => this.openModal('add-group-modal'));

        const compDisplay = document.getElementById('competition-name-display');
        if (compDisplay) {
            compDisplay.addEventListener('blur', () => {
                if (state.isAdmin) this.saveCompetitionNameInline();
            });
            compDisplay.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    compDisplay.blur();
                }
            });
        }

        const t1Score = document.getElementById('edit-t1-score');
        const t2Score = document.getElementById('edit-t2-score');
        if (t1Score) t1Score.addEventListener('input', () => this.saveMatchData());
        if (t2Score) t2Score.addEventListener('input', () => this.saveMatchData());

        // TomSelect Elements
        if (document.getElementById('group-selector')) {
            this.tsGroup = new TomSelect('#group-selector', {
                create: false,
                placeholder: "Pilih Grup...",
                onChange: (val) => this.onGroupSelected(val)
            });
        }
        if (document.getElementById('home-team-selector')) {
            this.tsHome = new TomSelect('#home-team-selector', { create: false, placeholder: "Pilih Tim Home..." });
        }
        if (document.getElementById('away-team-selector')) {
            this.tsAway = new TomSelect('#away-team-selector', { create: false, placeholder: "Pilih Tim Away..." });
        }
        if (document.getElementById('history-sort')) {
            this.tsHistorySort = new TomSelect('#history-sort', {
                create: false,
                controlInput: null,
                onChange: (val) => {
                    state.historySort = val;
                    this.renderHistory();
                }
            });
        }
        if (document.getElementById('log-action-filter')) {
            this.tsLogAction = new TomSelect('#log-action-filter', {
                create: false,
                onChange: () => this.filterLogs()
            });
        }
    },

    getHeaders() {
        return {
            'Content-Type': 'application/json',
            ...(state.token ? { 'Authorization': `Bearer ${state.token}` } : {})
        };
    },

    openModal(id) {
        const m = document.getElementById(id);
        if (m) m.classList.remove('hidden');
    },

    closeModal(id) {
        const m = document.getElementById(id);
        if (m) m.classList.add('hidden');
        if (id === 'login-modal') {
            const u = document.getElementById('admin-username');
            const p = document.getElementById('admin-password');
            const err = document.getElementById('login-error');
            if (u) u.value = '';
            if (p) p.value = '';
            if (err) err.classList.add('hidden');
        }
    },

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        const themeBtn = document.getElementById('theme-toggle-btn');
        if (themeBtn) {
            themeBtn.style.transition = 'transform 0.3s ease, opacity 0.3s ease';
            themeBtn.style.transform = 'rotate(180deg) scale(0.5)';
            themeBtn.style.opacity = '0';
            setTimeout(() => {
                themeBtn.innerText = newTheme === 'dark' ? '🌙' : '☀️';
                themeBtn.style.transform = 'rotate(360deg) scale(1)';
                themeBtn.style.opacity = '1';
                setTimeout(() => {
                    themeBtn.style.transition = 'none';
                    themeBtn.style.transform = 'none';
                }, 300);
            }, 150);
        }
    },

    toggleProfileDropdown() {
        const dropdown = document.getElementById('profile-dropdown');
        if (dropdown) dropdown.classList.toggle('hidden');
    },

    async login() {
        const usr = document.getElementById('admin-username').value;
        const pwd = document.getElementById('admin-password').value;
        try {
            const res = await fetch(`${API_URL}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: usr, password: pwd })
            });
            const data = await res.json();
            if (res.ok) {
                localStorage.setItem('adminToken', data.token);
                localStorage.setItem('adminUsername', data.username);
                localStorage.setItem('adminRole', data.role);
                this.checkLoginStatus();
                this.closeModal('login-modal');
                await this.fetchGroups();
            } else {
                const err = document.getElementById('login-error');
                if (err) {
                    err.innerText = data.message || "Password salah.";
                    err.classList.remove('hidden');
                }
            }
        } catch (e) {
            app.showAlert("Gagal terhubung ke API backend.");
        }
    },

    logout() {
        localStorage.removeItem('adminToken');
        localStorage.removeItem('adminUsername');
        localStorage.removeItem('adminRole');
        this.logoutState();
    },

    logoutState() {
        state.isAdmin = false;
        state.token = null;
        state.username = null;
        state.role = null;

        document.body.classList.remove('admin-mode');
        const lBtn = document.getElementById('admin-login-btn');
        if (lBtn) {
            lBtn.classList.remove('hidden');
            lBtn.innerText = 'Admin Login';
        }

        const pContainer = document.getElementById('admin-profile-container');
        const pDropdown = document.getElementById('profile-dropdown');
        const vLogs = document.getElementById('dropdown-view-logs');
        const sEditor = document.getElementById('score-editor');
        const lActions = document.getElementById('live-match-actions');

        if (pContainer) pContainer.classList.add('hidden');
        if (pDropdown) pDropdown.classList.add('hidden');
        if (vLogs) vLogs.classList.add('hidden');
        if (sEditor) sEditor.classList.add('hidden');
        if (lActions) lActions.style.display = 'none';

        this.fetchGroups();
    },

    async changePassword() {
        const old_password = document.getElementById('old-password').value;
        const new_password = document.getElementById('new-password').value;
        if (!old_password || !new_password) {
            return app.showAlert("Semua field harus diisi!");
        }
        try {
            const res = await fetch(`${API_URL}/user/password`, {
                method: 'PUT',
                headers: this.getHeaders(),
                body: JSON.stringify({ old_password, new_password })
            });
            const data = await res.json();
            if (res.ok) {
                app.showAlert("Password berhasil diubah!");
                this.closeModal('password-modal');
                document.getElementById('old-password').value = '';
                document.getElementById('new-password').value = '';
            } else {
                app.showAlert(data.message || "Gagal mengubah password.");
            }
        } catch (e) {
            app.showAlert("Gagal mengubah password.");
        }
    },

    async fetchAdmins() {
        if (state.role !== 'superadmin') return;
        try {
            const res = await fetch(`${API_URL}/users`, { headers: this.getHeaders() });
            const users = await res.json();
            const list = document.getElementById('admin-list');
            if (list) {
                list.innerHTML = users.map(u => `
                    <div class="admin-item" data-username="${u.username.toLowerCase()}" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem; padding:0.5rem; background:rgba(255,255,255,0.05); border-radius:6px;">
                        <div>
                            <strong style="color:var(--text-main);">${u.username}</strong>
                            <span style="font-size:0.8rem; color:var(--text-muted); margin-left:0.5rem;">(${u.role})</span>
                        </div>
                        ${u.username !== state.username ? `
                            <button class="btn-sm" style="border-color:#ff0055; color:#ff0055; background:transparent;" onclick="app.deleteAdmin('${u._id}')">Delete</button>
                        ` : '<span style="font-size:0.8rem; color:var(--primary); font-weight:bold;">You</span>'}
                    </div>
                `).join('');
            }
        } catch (e) {
            console.error("Gagal mengambil daftar admin", e);
        }
    },

    openManageAdminsModal() {
        this.openModal('manage-admins-modal');
        this.fetchAdmins();
    },

    filterAdmins() {
        const query = (document.getElementById('admin-search').value || '').toLowerCase();
        const items = document.querySelectorAll('.admin-item');
        items.forEach(item => {
            const username = item.getAttribute('data-username') || '';
            item.style.display = username.includes(query) ? 'flex' : 'none';
        });
    },

    async createAdmin() {
        const username = document.getElementById('new-admin-user').value.trim();
        const password = document.getElementById('new-admin-pass').value;
        if (!username || !password) {
            return app.showAlert("Username dan password wajib diisi!");
        }
        try {
            const res = await fetch(`${API_URL}/users`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ username, password })
            });
            const data = await res.json();
            if (res.ok) {
                app.showAlert("Admin berhasil ditambahkan!");
                document.getElementById('new-admin-user').value = '';
                document.getElementById('new-admin-pass').value = '';
                this.fetchAdmins();
            } else {
                app.showAlert(data.message || "Gagal menambahkan admin.");
            }
        } catch (e) {
            app.showAlert("Gagal menambahkan admin.");
        }
    },

    async deleteAdmin(userId) {
        if (!await app.showConfirm("Hapus admin ini?")) return;
        try {
            const res = await fetch(`${API_URL}/users/${userId}`, {
                method: 'DELETE',
                headers: this.getHeaders()
            });
            const data = await res.json();
            if (res.ok) {
                this.fetchAdmins();
            } else {
                app.showAlert(data.message || "Gagal menghapus admin.");
            }
        } catch (e) {
            app.showAlert("Gagal menghapus admin.");
        }
    },

    async fetchSettings() {
        try {
            const res = await fetch(`${API_URL}/settings`);
            const data = await res.json();
            if (data && (data.competitionName || data.competition_name)) {
                const name = data.competitionName || data.competition_name;
                state.competitionName = name;
                const compDisplay = document.getElementById('competition-name-display');
                if (compDisplay) {
                    compDisplay.innerHTML = name.replace(' ', ' <span>') + '</span>';
                }
            }
        } catch (e) {
            console.error("Could not fetch settings", e);
        }
    },

    async saveCompetitionNameInline() {
        const h1 = document.getElementById('competition-name-display');
        if (!h1) return;
        let name = h1.innerText.trim();
        if (!name || name === state.competitionName) return;

        try {
            await fetch(`${API_URL}/settings`, {
                method: 'PUT',
                headers: this.getHeaders(),
                body: JSON.stringify({ competition_name: name })
            });
            state.competitionName = name;
            const firstSpace = name.indexOf(' ');
            if (firstSpace !== -1) {
                h1.innerHTML = name.substring(0, firstSpace) + ' <span>' + name.substring(firstSpace + 1) + '</span>';
            } else {
                h1.innerHTML = name;
            }
            this.showToast('Sukses', 'Nama turnamen berhasil diubah!');
        } catch (e) {
            console.error(e);
            this.showToast('Error', 'Gagal mengubah nama turnamen');
        }
    },

    async fetchGroups() {
        try {
            const includeHidden = state.role === 'superadmin' ? '?include_hidden=true' : '';
            const res = await fetch(`${API_URL}/groups${includeHidden}`, {
                headers: this.getHeaders(),
                cache: 'no-store'
            });
            const data = await res.json();
            state.groups = data;
            this.renderGroups();
            this.renderHistory();
            if (state.isAdmin) {
                this.updateGroupSelector();
            }
            this.updateLiveMatchDisplay();
        } catch (e) {
            console.error("Could not fetch groups", e);
            const grid = document.getElementById('groups-grid');
            if (grid) grid.innerHTML = '<p class="placeholder-text">Error loading from database. Make sure Python API is running.</p>';
        }
    },

    // PERBAIKAN UTAMA: Mengirim Array String `teams` sesuai kontrak Backend Flask
    async createGroup() {
        const name = document.getElementById('new-group-name').value.trim();
        const teamsStr = document.getElementById('new-group-teams').value;
        if (!name || !teamsStr) return app.showAlert("Harap isi semua kolom!");

        const teams = teamsStr.split(',').map(s => s.trim()).filter(s => s);
        if (teams.length < 2) return app.showAlert("Harap sediakan minimal 2 tim!");

        try {
            const res = await fetch(`${API_URL}/groups`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ name, teams })
            });
            if (res.ok) {
                this.closeModal('add-group-modal');
                document.getElementById('new-group-name').value = '';
                document.getElementById('new-group-teams').value = '';
                await this.fetchGroups();
            } else {
                const data = await res.json();
                app.showAlert(data.message || "Gagal membuat grup.");
            }
        } catch (e) {
            app.showAlert("Gagal membuat grup.");
        }
    },

    async deleteGroup(groupId, permanent = false) {
        const confirmMsg = permanent 
            ? "PERINGATAN: Hapus grup ini secara permanen beserta semua data pertandingannya?" 
            : "Sembunyikan grup ini?";
        if (!await app.showConfirm(confirmMsg)) return;

        try {
            const url = permanent ? `${API_URL}/groups/${groupId}?permanent=true` : `${API_URL}/groups/${groupId}`;
            const res = await fetch(url, { method: 'DELETE', headers: this.getHeaders() });
            if (res.ok) {
                await this.fetchGroups();
            } else {
                app.showAlert("Gagal menghapus/menyembunyikan grup.");
            }
        } catch (e) {
            app.showAlert("Error menghapus/menyembunyikan grup.");
        }
    },

    async restoreGroup(groupId) {
        if (!await app.showConfirm("Tampilkan kembali grup ini?")) return;
        try {
            const res = await fetch(`${API_URL}/groups/${groupId}`, {
                method: 'PUT',
                headers: this.getHeaders(),
                body: JSON.stringify({ isHidden: false })
            });
            if (res.ok) {
                await this.fetchGroups();
            } else {
                app.showAlert("Gagal memulihkan grup.");
            }
        } catch (e) {
            app.showAlert("Error memulihkan grup.");
        }
    },

    openEditGroup(groupId) {
        const group = state.groups.find(g => g._id === groupId);
        if (!group) return;
        document.getElementById('edit-group-id').value = groupId;
        document.getElementById('edit-group-name-input').value = group.name;
        const container = document.getElementById('edit-group-teams-container');
        container.innerHTML = group.teams.map(t => `
            <div style="display:flex; gap:0.5rem; margin-bottom:0.5rem; align-items:center;">
                <input type="hidden" class="edit-team-id" value="${t.id}">
                <input type="text" class="edit-team-name custom-select" style="flex:2; margin-bottom:0;" value="${t.name}" placeholder="Nama Tim">
                <input type="text" class="edit-team-code custom-select" style="width:70px; margin-bottom:0;" value="${t.code || ''}" placeholder="Kode">
            </div>
        `).join('');
        this.openModal('edit-group-modal');
    },

    async saveGroupName() {
        const groupId = document.getElementById('edit-group-id').value;
        const name = document.getElementById('edit-group-name-input').value;
        const teamElements = document.querySelectorAll('#edit-group-teams-container > div');
        const teams = Array.from(teamElements).map(el => ({
            id: el.querySelector('.edit-team-id').value,
            name: el.querySelector('.edit-team-name').value.trim(),
            code: el.querySelector('.edit-team-code').value.trim().toLowerCase()
        }));

        try {
            const res = await fetch(`${API_URL}/groups/${groupId}`, {
                method: 'PUT',
                headers: this.getHeaders(),
                body: JSON.stringify({ name, teams })
            });
            if (res.ok) {
                this.closeModal('edit-group-modal');
                await this.fetchGroups();
            } else {
                app.showAlert("Gagal menyimpan perubahan");
            }
        } catch (e) {
            app.showAlert("Error menyimpan grup");
        }
    },

    isTeamLive(teamId) {
        for (let g of state.groups) {
            let liveMatch = g.matches.find(m => m.isLive === true || m.status === 'live');
            if (liveMatch && (liveMatch.team1.id === teamId || liveMatch.team2.id === teamId)) {
                return true;
            }
        }
        return false;
    },

    calculateStandings(group) {
        let standings = group.teams.map(t => ({ ...t, p: 0, w: 0, d: 0, l: 0, gf: 0, ga: 0, gd: 0, pts: 0, form: [] }));
        const finishedMatches = group.matches.filter(m => m.isFinished === true || m.status === 'finished');
        finishedMatches.sort((a, b) => (a.playOrder || 0) - (b.playOrder || 0));

        finishedMatches.forEach(m => {
            const t1 = standings.find(t => t.id === m.team1.id);
            const t2 = standings.find(t => t.id === m.team2.id);
            if (!t1 || !t2) return;

            t1.p++; t2.p++;
            t1.gf += m.score1; t1.ga += m.score2;
            t2.gf += m.score2; t2.ga += m.score1;

            if (m.score1 > m.score2) {
                t1.w++; t1.pts += 3; t2.l++;
                t1.form.push('W'); t2.form.push('L');
            } else if (m.score1 < m.score2) {
                t2.w++; t2.pts += 3; t1.l++;
                t1.form.push('L'); t2.form.push('W');
            } else {
                t1.d++; t1.pts += 1; t2.d++; t2.pts += 1;
                t1.form.push('D'); t2.form.push('D');
            }
        });

        standings.forEach(t => {
            t.gd = t.gf - t.ga;
            t.form = t.form.slice(-5);
        });

        standings.sort((a, b) => {
            if (b.pts !== a.pts) return b.pts - a.pts;
            if (b.gd !== a.gd) return b.gd - a.gd;
            return b.gf - a.gf;
        });

        return standings;
    },

    getFormHtml(formArray) {
        if (!formArray || formArray.length === 0) return '<span style="color:var(--text-muted); font-size:0.8rem;">-</span>';
        return `<div class="form-circles">` + formArray.map(res => {
            let colorClass = res === 'W' ? 'form-w' : res === 'D' ? 'form-d' : 'form-l';
            return `<span class="form-circle ${colorClass}">${res}</span>`;
        }).join('') + `</div>`;
    },

    renderGroups() {
        const grid = document.getElementById('groups-grid');
        if (!grid) return;
        grid.innerHTML = '';

        state.groups.forEach(group => {
            const standings = this.calculateStandings(group);
            let rowsHtml = standings.map((t, i) => {
                const liveBadge = this.isTeamLive(t.id) ? `<span class="live-indicator">LIVE</span>` : '';
                return `
                    <tr>
                        <td style="color: var(--text-muted)">${i + 1}</td>
                        <td class="left-align">
                            <div class="team-info">
                                <img src="${getFlagUrl(t.code)}" alt="${t.name}">
                                <span>${t.name}</span> ${liveBadge}
                            </div>
                        </td>
                        <td>${t.p}</td>
                        <td>${t.w}</td>
                        <td>${t.d}</td>
                        <td>${t.l}</td>
                        <td>${t.gf}</td>
                        <td>${t.ga}</td>
                        <td>${t.gd > 0 ? '+' + t.gd : t.gd}</td>
                        <td class="pts-col">${t.pts}</td>
                        <td>${this.getFormHtml(t.form)}</td>
                    </tr>
                `;
            }).join('');

            const card = document.createElement('div');
            card.className = 'glass-panel group-card' + (group.isHidden ? ' hidden-group' : '');
            if (group.isHidden) {
                card.style.opacity = '0.65';
                card.style.border = '2px dashed #ff9900';
            }

            let headerActions = group.isHidden ? `
                <button class="btn-sm btn-restore" onclick="app.restoreGroup('${group._id}')">Restore</button>
                <button class="btn-sm btn-outline" onclick="app.deleteGroup('${group._id}', true)" style="border-color:#ff0055; color:#ff0055;">Delete</button>
            ` : `
                <button class="btn-sm btn-edit" onclick="app.openEditGroup('${group._id}')">Edit</button>
                <button class="btn-sm btn-outline" onclick="app.deleteGroup('${group._id}', false)" style="border-color: #ff0055; color: #ff0055;">Delete</button>
            `;

            card.innerHTML = `
                <div class="group-header">
                    <h3>${group.name} ${group.isHidden ? '<span style="background:#ff9900; color:white; padding:0.15rem 0.4rem; border-radius:4px; font-size:0.7rem; font-weight:bold; vertical-align:middle; margin-left:0.5rem;">HIDDEN</span>' : ''}</h3>
                    <div class="admin-only-flex" style="gap:0.5rem;">${headerActions}</div>
                </div>
                <table class="standings-table">
                    <thead>
                        <tr>
                            <th width="30">#</th>
                            <th class="left-align">TEAM</th>
                            <th width="30">MP</th><th width="30">W</th><th width="30">D</th><th width="30">L</th>
                            <th width="30">GM</th><th width="30">GK</th><th width="40">GD</th><th width="40">PTS</th>
                            <th width="120">FORM</th>
                        </tr>
                    </thead>
                    <tbody>${rowsHtml}</tbody>
                </table>
            `;
            grid.appendChild(card);
        });
    },

    updateGroupSelector() {
        if (!this.tsGroup) return;
        this.tsGroup.clear();
        this.tsGroup.clearOptions();
        state.groups.forEach(g => {
            let text = g.name + (g.isHidden ? ' [HIDDEN]' : '');
            this.tsGroup.addOption({ value: g._id, text: text });
        });
        this.tsGroup.setValue("");
        const ts = document.getElementById('team-selectors');
        const smBtn = document.getElementById('start-match-btn');
        if (ts) ts.style.display = 'none';
        if (smBtn) smBtn.style.display = 'none';
    },

    onGroupSelected(groupId) {
        if (!groupId || !this.tsHome || !this.tsAway) {
            const ts = document.getElementById('team-selectors');
            const smBtn = document.getElementById('start-match-btn');
            if (ts) ts.style.display = 'none';
            if (smBtn) smBtn.style.display = 'none';
            return;
        }

        const group = state.groups.find(g => g._id === groupId);
        if (!group) return;

        this.tsHome.clear();
        this.tsHome.clearOptions();
        this.tsAway.clear();
        this.tsAway.clearOptions();

        group.teams.forEach(t => {
            this.tsHome.addOption({ value: t.id, text: t.name });
            this.tsAway.addOption({ value: t.id, text: t.name });
        });

        this.tsHome.setValue("");
        this.tsAway.setValue("");
        document.getElementById('team-selectors').style.display = 'flex';
        document.getElementById('start-match-btn').style.display = 'block';
    },

    async startMatch(force = false) {
        const groupId = this.tsGroup.getValue();
        const homeId = this.tsHome.getValue();
        const awayId = this.tsAway.getValue();

        if (!groupId || !homeId || !awayId) {
            return app.showAlert("Pilih grup dan kedua tim terlebih dahulu!");
        }
        if (homeId === awayId) {
            return app.showAlert("Tim home dan away tidak boleh sama!");
        }

        try {
            const res = await fetch(`${API_URL}/matches/start`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ groupId, homeTeamId: homeId, awayTeamId: awayId, force })
            });
            const data = await res.json();
            if (res.ok) {
                state.currentGroupId = groupId;
                state.currentMatchId = data.id || data.matchId;
                await this.fetchGroups();
                this.openLiveScoreEditor(state.currentMatchId);
                this.showToast('Match Started', 'Live match berhasil dimulai!');
            } else {
                app.showAlert(data.message || "Gagal memulai pertandingan.");
            }
        } catch (e) {
            app.showAlert("Gagal memulai pertandingan.");
        }
    },

    openLiveScoreEditor(matchId) {
        let match = null;
        for (let g of state.groups) {
            let found = g.matches.find(m => m._id === matchId);
            if (found) {
                match = found;
                state.currentGroupId = g._id;
                break;
            }
        }
        if (!match) return;
        state.currentMatchId = matchId;

        const sEditor = document.getElementById('score-editor');
        const lActions = document.getElementById('live-match-actions');
        if (sEditor) sEditor.classList.remove('hidden');
        if (lActions) lActions.style.display = 'flex';

        document.getElementById('edit-t1-name').innerText = match.team1.name;
        document.getElementById('edit-t2-name').innerText = match.team2.name;

        if (document.activeElement.id !== 'edit-t1-score') {
            document.getElementById('edit-t1-score').value = match.score1;
        }
        if (document.activeElement.id !== 'edit-t2-score') {
            document.getElementById('edit-t2-score').value = match.score2;
        }
    },

    async updateScore(team, diff) {
        const inputId = team === 'team1' ? 'edit-t1-score' : 'edit-t2-score';
        const input = document.getElementById(inputId);
        let val = parseInt(input.value) + diff;
        if (val < 0) val = 0;
        input.value = val;
        this.saveMatchData();
    },

    async saveMatchData() {
        if (!state.currentMatchId) return;
        const score1 = parseInt(document.getElementById('edit-t1-score').value) || 0;
        const score2 = parseInt(document.getElementById('edit-t2-score').value) || 0;

        try {
            await fetch(`${API_URL}/matches/${state.currentMatchId}`, {
                method: 'PUT',
                headers: this.getHeaders(),
                body: JSON.stringify({ score1, score2 })
            });

            for (let g of state.groups) {
                let m = g.matches.find(x => x._id === state.currentMatchId);
                if (m) {
                    m.score1 = score1;
                    m.score2 = score2;
                    break;
                }
            }
            this.updateLiveMatchDisplay();
        } catch (e) {
            console.error("Failed to save match data", e);
        }
    },

    async finishMatch() {
        if (!state.currentMatchId) return;
        try {
            await fetch(`${API_URL}/matches/${state.currentMatchId}/status`, {
                method: 'PUT',
                headers: this.getHeaders(),
                body: JSON.stringify({ isFinished: true })
            });

            document.getElementById('score-editor').classList.add('hidden');
            document.getElementById('live-match-actions').style.display = 'none';
            state.currentMatchId = null;
            app.showAlert("Match finished and standings updated!");
            await this.fetchGroups();
        } catch (e) {
            app.showAlert("Failed to finish match");
        }
    },

    async cancelLiveMatch() {
        if (!state.currentMatchId) return;
        if (!await app.showConfirm("Batalkan pertandingan langsung yang sedang berjalan?")) return;

        try {
            const res = await fetch(`${API_URL}/matches/${state.currentMatchId}/reset`, {
                method: 'DELETE',
                headers: this.getHeaders()
            });
            if (res.ok) {
                state.currentMatchId = null;
                document.getElementById('score-editor').classList.add('hidden');
                document.getElementById('live-match-actions').style.display = 'none';
                
                const container = document.getElementById('live-match-display');
                if (container) container.innerHTML = '<p class="placeholder-text">No match currently playing.</p>';

                this.updateGroupSelector();
                await this.fetchGroups();
            } else {
                app.showAlert("Gagal membatalkan pertandingan.");
            }
        } catch (e) {
            app.showAlert("Error membatalkan pertandingan.");
        }
    },

    updateLiveMatchDisplay() {
        const container = document.getElementById('live-match-display');
        if (!container) return;

        let liveMatch = null;
        for (let g of state.groups) {
            let found = g.matches.find(m => m.isLive === true || m.status === 'live');
            if (found) {
                liveMatch = found;
                break;
            }
        }

        if (!liveMatch) {
            container.innerHTML = '<p class="placeholder-text">No match currently playing.</p>';
            if (state.isAdmin) {
                document.getElementById('score-editor').classList.add('hidden');
                document.getElementById('live-match-actions').style.display = 'none';
            }
            return;
        }

        const t1 = liveMatch.team1;
        const t2 = liveMatch.team2;

        container.innerHTML = `
            <div class="match-score-board">
                <div class="team-display">
                    <span style="font-size:0.8rem; color:var(--text-muted); font-weight:bold; letter-spacing:1px; text-transform:uppercase; margin-bottom:-0.3rem;">HOME</span>
                    <img src="${getFlagUrl(t1.code)}" alt="${t1.name}">
                    <h3>${t1.name}</h3>
                </div>
                <div class="score-display">
                    <div class="score-num">${liveMatch.score1}</div>
                    <div class="vs-text">VS</div>
                    <div class="score-num">${liveMatch.score2}</div>
                </div>
                <div class="team-display">
                    <span style="font-size:0.8rem; color:var(--text-muted); font-weight:bold; letter-spacing:1px; text-transform:uppercase; margin-bottom:-0.3rem;">AWAY</span>
                    <img src="${getFlagUrl(t2.code)}" alt="${t2.name}">
                    <h3>${t2.name}</h3>
                </div>
            </div>
        `;

        if (state.isAdmin) {
            this.openLiveScoreEditor(liveMatch._id);
        }
    },

    getAllHistoryMatches() {
        let history = [];
        state.groups.forEach(g => {
            g.matches.forEach(m => {
                if (m.isFinished === true || m.status === 'finished') {
                    history.push({ ...m, groupName: g.name });
                }
            });
        });

        if (state.historySort === 'time') {
            history.sort((a, b) => (b.playOrder ?? -1) - (a.playOrder ?? -1));
        } else {
            history.sort((a, b) => {
                if (a.groupName !== b.groupName) return a.groupName.localeCompare(b.groupName);
                return (b.playOrder ?? -1) - (a.playOrder ?? -1);
            });
        }
        return history;
    },

    renderHistory() {
        const container = document.getElementById('history-list');
        if (!container) return;
        container.innerHTML = '';

        const history = this.getAllHistoryMatches();
        if (history.length === 0) {
            container.innerHTML = '<p class="placeholder-text">No matches played yet.</p>';
            return;
        }

        history.forEach((m, index) => {
            if (m.isHidden && state.role !== 'superadmin') return;

            const item = document.createElement('div');
            item.className = 'history-item' + (m.isHidden ? ' hidden-match' : '');
            if (m.isHidden) {
                item.style.opacity = '0.65';
                item.style.border = '2px dashed #ff9900';
            }

            let actionButtons = '';
            if (m.isHidden && state.role === 'superadmin') {
                actionButtons = `
                    <button class="btn-sm btn-restore" onclick="app.restoreMatch('${m._id}')">Restore</button>
                    <button class="btn-sm btn-outline" onclick="app.deleteMatch('${m._id}', true)" style="border-color:#ff0055; color:#ff0055;">Delete Permanently</button>
                `;
            } else if (!m.isHidden) {
                actionButtons = `
                    <button class="btn-sm btn-edit" onclick="app.openEditHistory('${m._id}')">Edit</button>
                    <button class="btn-sm btn-outline" onclick="app.deleteMatch('${m._id}', false)" style="border-color:#ff0055; color:#ff0055;">Delete</button>
                `;
            }

            item.innerHTML = `
                <div class="history-match-info">
                    <div style="font-size: 0.8rem; color: var(--text-muted); font-weight: bold; width: 60px;">
                        ${m.groupName} ${m.isHidden ? '<span style="background:#ff9900; color:white; padding:0.05rem 0.2rem; border-radius:3px; font-size:0.55rem; font-weight:bold; display:block; width:fit-content; margin-top:2px;">HIDDEN</span>' : ''}
                    </div>
                    <div class="history-team home">
                        <span>${m.team1.name}</span>
                        <img src="${getFlagUrl(m.team1.code)}" alt="${m.team1.name}">
                    </div>
                    <div class="history-score">
                        <span>${m.score1}</span>
                        <span style="font-size: 1rem; color: var(--text-muted); font-weight: 300;">-</span>
                        <span>${m.score2}</span>
                    </div>
                    <div class="history-team away">
                        <img src="${getFlagUrl(m.team2.code)}" alt="${m.team2.name}">
                        <span>${m.team2.name}</span>
                    </div>
                </div>
                <div class="history-actions ${state.isAdmin ? '' : 'hidden'}">
                    ${actionButtons}
                    <div class="history-reorder-btns ${state.role === 'superadmin' && !m.isHidden ? '' : 'hidden'}" style="cursor: grab; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; padding: 0 10px; color: var(--text-muted);">
                        <span title="Drag to reorder">☰</span>
                    </div>
                </div>
            `;
            container.appendChild(item);

            if (state.role === 'superadmin' && state.historySort === 'time') {
                item.setAttribute('draggable', 'true');
                item.addEventListener('dragstart', (e) => {
                    e.dataTransfer.effectAllowed = 'move';
                    e.dataTransfer.setData('text/plain', index.toString());
                    item.style.opacity = '0.5';
                });
                item.addEventListener('dragend', () => {
                    item.style.opacity = '';
                    document.querySelectorAll('.history-item').forEach(el => {
                        el.style.borderTop = '';
                        el.style.borderBottom = '';
                    });
                });
                item.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    return false;
                });
                item.addEventListener('dragenter', (e) => {
                    e.preventDefault();
                    item.style.borderTop = '2px solid var(--primary)';
                });
                item.addEventListener('dragleave', () => {
                    item.style.borderTop = '';
                });
                item.addEventListener('drop', (e) => {
                    e.stopPropagation();
                    const fromIndex = parseInt(e.dataTransfer.getData('text/plain'));
                    if (fromIndex !== index && !isNaN(fromIndex)) {
                        app.reorderMatchDrag(fromIndex, index);
                    }
                    return false;
                });
            }
        });
    },

    async reorderMatchDrag(fromIndex, toIndex) {
        const history = this.getAllHistoryMatches();
        if (fromIndex < 0 || fromIndex >= history.length || toIndex < 0 || toIndex >= history.length) return;

        const [movedItem] = history.splice(fromIndex, 1);
        history.splice(toIndex, 0, movedItem);

        const orderIds = history.map(m => m._id).reverse();

        try {
            const res = await fetch(`${API_URL}/matches/reorder`, {
                method: 'PUT',
                headers: this.getHeaders(),
                body: JSON.stringify({ order: orderIds })
            });
            if (res.ok) {
                await this.fetchGroups();
                this.showToast('Match History Reordered', 'Urutan berhasil disimpan!');
            } else {
                app.showAlert("Failed to update ordering.");
            }
        } catch (e) {
            console.error("Gagal mengubah urutan histori", e);
        }
    },

    openEditHistory(matchId) {
        let match = null;
        for (let g of state.groups) {
            let found = g.matches.find(m => m._id === matchId);
            if (found) {
                match = found;
                break;
            }
        }
        if (!match) return;

        document.getElementById('edit-history-match-id').value = matchId;
        document.getElementById('hist-t1-name').innerText = match.team1.name;
        document.getElementById('hist-t2-name').innerText = match.team2.name;
        document.getElementById('hist-t1-score').value = match.score1;
        document.getElementById('hist-t2-score').value = match.score2;

        this.openModal('edit-history-modal');
    },

    async saveHistoryScore() {
        const matchId = document.getElementById('edit-history-match-id').value;
        const score1 = parseInt(document.getElementById('hist-t1-score').value) || 0;
        const score2 = parseInt(document.getElementById('hist-t2-score').value) || 0;

        try {
            const res = await fetch(`${API_URL}/matches/${matchId}`, {
                method: 'PUT',
                headers: this.getHeaders(),
                body: JSON.stringify({ score1, score2 })
            });
            if (res.ok) {
                this.closeModal('edit-history-modal');
                await this.fetchGroups();
            } else {
                app.showAlert("Gagal memperbarui skor.");
            }
        } catch (e) {
            app.showAlert("Error memperbarui skor.");
        }
    },

    async deleteMatch(matchId, permanent = false) {
        const confirmMsg = permanent 
            ? "PERINGATAN: Hapus hasil pertandingan ini secara permanen?" 
            : "Sembunyikan hasil pertandingan ini?";
        if (!await app.showConfirm(confirmMsg)) return;

        try {
            const url = permanent ? `${API_URL}/matches/${matchId}/reset?permanent=true` : `${API_URL}/matches/${matchId}/reset`;
            const res = await fetch(url, { method: 'DELETE', headers: this.getHeaders() });
            if (res.ok) {
                await this.fetchGroups();
            } else {
                app.showAlert("Gagal menghapus hasil pertandingan.");
            }
        } catch (e) {
            app.showAlert("Error menghapus hasil pertandingan.");
        }
    },

    async restoreMatch(matchId) {
        if (!await app.showConfirm("Tampilkan kembali hasil pertandingan ini?")) return;
        try {
            const res = await fetch(`${API_URL}/matches/${matchId}`, {
                method: 'PUT',
                headers: this.getHeaders(),
                body: JSON.stringify({ isHidden: false })
            });
            if (res.ok) {
                await this.fetchGroups();
            } else {
                app.showAlert("Gagal memulihkan hasil pertandingan.");
            }
        } catch (e) {
            app.showAlert("Error memulihkan hasil pertandingan.");
        }
    },

    async openLogsModal() {
        this.openModal('logs-modal');
        await this.fetchLogs(false);
    },

    async fetchLogs(showNotifications = false) {
        if (!state.isAdmin || state.role !== 'superadmin') return;
        try {
            const res = await fetch(`${API_URL}/logs`, { headers: this.getHeaders() });
            if (res.ok) {
                const logs = await res.json();
                if (showNotifications && state.logs.length > 0) {
                    const newLogs = logs.filter(log => {
                        const isNew = !state.logs.some(existing => existing._id === log._id);
                        const isOtherAdmin = log.username !== state.username;
                        return isNew && isOtherAdmin;
                    });
                    newLogs.reverse().forEach(log => {
                        let actionLabel = log.action.replace('_', ' ');
                        this.showToast(log.username, `${actionLabel}: ${log.details}`);
                    });
                }
                state.logs = logs;
                this.renderLogs();
            }
        } catch (e) {
            console.error("Gagal mengambil log aktivitas", e);
        }
    },

    renderLogs() {
        const container = document.getElementById('logs-container');
        if (!container) return;

        const searchVal = (document.getElementById('log-search')?.value || '').toLowerCase();
        const actionFilter = this.tsLogAction ? this.tsLogAction.getValue() : '';

        const filtered = state.logs.filter(log => {
            const matchesSearch = log.username.toLowerCase().includes(searchVal) || 
                                  log.action.toLowerCase().includes(searchVal) || 
                                  log.details.toLowerCase().includes(searchVal);
            const matchesAction = !actionFilter || log.action === actionFilter;
            return matchesSearch && matchesAction;
        });

        if (filtered.length === 0) {
            container.innerHTML = '<p class="placeholder-text" style="text-align:center; padding:2rem 0;">No logs found.</p>';
            return;
        }

        container.innerHTML = filtered.map(log => {
            const time = new Date(log.timestamp).toLocaleString();
            let actionStyle = 'background:var(--primary); color:white; padding:0.2rem 0.5rem; border-radius:4px; font-weight:bold;';
            if (log.action.includes('DELETE') || log.action.includes('RESET')) {
                actionStyle = 'background:#ff0055; color:white; padding:0.2rem 0.5rem; border-radius:4px; font-weight:bold;';
            } else if (log.action.includes('CREATE') || log.action.includes('START') || log.action.includes('FINISH')) {
                actionStyle = 'background:#00cc66; color:white; padding:0.2rem 0.5rem; border-radius:4px; font-weight:bold;';
            }

            return `
                <div style="background:var(--bg-dark); border:1px solid var(--border-color); padding:1rem; border-radius:10px; display:flex; flex-direction:column; gap:0.4rem; position:relative;">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
                        <span style="font-weight:bold; color:var(--primary); font-size:0.95rem;">@${log.username}</span>
                        <span style="${actionStyle} font-size:0.75rem; text-transform:uppercase;">${log.action.replace('_', ' ')}</span>
                    </div>
                    <p style="font-size:0.9rem; color:var(--text-main); margin:0;">${log.details}</p>
                    <span style="font-size:0.75rem; color:var(--text-muted); align-self:flex-end;">${time}</span>
                </div>
            `;
        }).join('');
    },

    filterLogs() {
        this.renderLogs();
    },

    showToast(title, message) {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.innerHTML = `
            <div style="font-weight:bold; color:var(--primary); font-size:0.9rem; display:flex; align-items:center; gap:0.5rem;">
                <span style="color:#ff0055;">●</span> Action Alert
            </div>
            <strong style="color:var(--text-main); font-size:0.85rem; margin-top:0.2rem;">@${title}</strong>
            <span style="font-size:0.8rem; color:var(--text-muted);">${message}</span>
        `;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) reverse forwards';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    },

    setupRealtimeUpdates() {
        if (window.eventSource) {
            window.eventSource.close();
        }
        const baseUrl = API_URL.replace('/api', '');
        const source = new EventSource(`${baseUrl}/api/events`);

        source.onmessage = async (event) => {
            if (event.data === 'update') {
                await this.fetchGroups();
                if (state.isAdmin && state.role === 'superadmin') {
                    await this.fetchLogs(true);
                }
            }
        };

        source.onerror = (err) => {
            console.warn("EventSource connection issue. Retrying...", err);
        };

        window.eventSource = source;
    }
};

window.onload = () => app.init();
