let currentTool = null;
let runningTools = [];
let toolConfigs = {};

function saveState() {
    localStorage.setItem('toolConfigs', JSON.stringify(toolConfigs));
}

function loadState() {
    const savedConfigs = localStorage.getItem('toolConfigs');
    if (savedConfigs) toolConfigs = JSON.parse(savedConfigs);

    fetch("http://localhost:8000/tools/containers?created_by=mon_app")
        .then(res => res.json())
        .then(data => {
            runningTools = [];
            const containers = data.containers || [];

            renderAllContainers(containers);

            containers.forEach(c => {
                const tool = detectToolFromName(c.name);
                if (tool) {
                    runningTools.push(tool);
                    updateStatus(tool, true);
                }
            });

            updateRunningList();
        })
        .catch(err => console.error("Erreur récupération des conteneurs:", err));
}

function detectToolFromName(name) {
    name = name.toLowerCase();
    if (name.includes("spark")) return "spark";
    if (name.includes("hbase")) return "hbase";
    if (name.includes("mongo")) return "mongodb";
    return null;
}

function setOutput(msg) {
    const outputEl = document.getElementById('output');
    if (outputEl) outputEl.textContent = msg;
}

function updateStatus(tool, isRunning) {
    const statusEl = document.getElementById(`status-${tool}`);
    if (statusEl) {
        statusEl.classList.remove('green', 'red');
        statusEl.classList.add(isRunning ? 'green' : 'red');
    }

    if (isRunning && !runningTools.includes(tool)) {
        runningTools.push(tool);
    } else if (!isRunning) {
        runningTools = runningTools.filter(t => t !== tool);
        delete toolConfigs[tool];
    }

    updateRunningList();
    saveState();
}

function updateRunningList() {
    const list = document.getElementById('runningList');
    if (!list) return;
    list.innerHTML = '';
    runningTools.forEach(tool => {
        const li = document.createElement('li');
        li.textContent = tool.charAt(0).toUpperCase() + tool.slice(1) + ' ';

        const configBtn = document.createElement('button');
        configBtn.textContent = "Configurer";
        configBtn.className = "config-button";
        configBtn.id = `config-btn-${tool}`;
        configBtn.onclick = () => showConfigModal(tool);

        li.appendChild(configBtn);

        const countdownSpan = document.createElement('span');
        countdownSpan.id = `countdown-${tool}`;
        countdownSpan.style.marginLeft = "10px";
        li.appendChild(countdownSpan);

        list.appendChild(li);
    });
}

function disableConfigTemporarily(tool, seconds) {
    const button = document.getElementById(`config-btn-${tool}`);
    const countdown = document.getElementById(`countdown-${tool}`);

    if (!button || !countdown) return;

    button.disabled = true;
    button.style.opacity = "0.5";
    countdown.textContent = `(${seconds}s)`;

    const interval = setInterval(() => {
        seconds--;
        if (seconds <= 0) {
            clearInterval(interval);
            button.disabled = false;
            button.style.opacity = "1";
            countdown.textContent = "";
        } else {
            countdown.textContent = `(${seconds}s)`;
        }
    }, 1000);
}

async function startTool(tool) {
    showCustomizeModal(tool);
}

async function stopTool(tool) {
    const config = toolConfigs[tool];
    if (!config) {
        setOutput("Aucune configuration trouvée pour cet outil.");
        return;
    }

    setOutput(`Arrêt de ${tool}...`);

    try {
        const response = await fetch(`http://localhost:8000/tools/${tool}/stop`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const data = await response.json();

        if (response.ok) {
            setOutput(`${tool} arrêté avec succès !`);
            updateStatus(tool, false);
        } else {
            setOutput(`Erreur : ${data.detail || 'Échec de l\'arrêt de ' + tool}`);
        }
    } catch (err) {
        setOutput(`Erreur : ${err}`);
    }
}

function showCustomizeModal(tool) {
    currentTool = tool;
    const el = document.getElementById('customToolName');
    if (el) el.textContent = tool.charAt(0).toUpperCase() + tool.slice(1);

    document.getElementById('container_name').value = '';
    document.getElementById('username').value = '';
    document.getElementById('password').value = '';
    document.getElementById('port').value = '8080';
    document.getElementById('customModal').style.display = 'block';
}

async function submitCustomization() {
    const container_name = document.getElementById('container_name').value.trim();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();
    const port = parseInt(document.getElementById('port').value.trim());

    if (!container_name || !username || !password || isNaN(port)) {
        setOutput('Tous les champs sont requis avec un port valide !');
        return;
    }

    document.getElementById('customModal').style.display = 'none';
    setOutput(`Démarrage de ${currentTool} avec la configuration personnalisée...`);

    try {
        const response = await fetch(`http://localhost:8000/tools/${currentTool}/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ container_name, username, password, port })
        });
        const data = await response.json();
        if (response.ok) {
            setOutput(`${currentTool} démarré avec succès !`);
            toolConfigs[currentTool] = { container_name, username, password, port };
            updateStatus(currentTool, true);
        } else {
            setOutput(`Erreur : ${data.detail || 'Échec du démarrage de ' + currentTool}`);
        }
    } catch (err) {
        setOutput(`Erreur : ${err}`);
    }
}

async function showConfigModal(tool) {
    const config = toolConfigs[tool];
    if (!config) {
        alert("Configuration non disponible !");
        return;
    }

    let html = `
        <h3>Configuration Docker</h3>
        <p><strong>Outil :</strong> ${tool.charAt(0).toUpperCase() + tool.slice(1)}</p>
        <p><strong>Nom du conteneur :</strong> ${config.container_name}</p>
        <p><strong>Nom d'utilisateur :</strong> ${config.username}</p>
        <p><strong>Mot de passe :</strong> ${config.password}</p>
        <p><strong>Port :</strong> ${config.port}</p>
        <hr>
        <h3>Configuration Interne</h3>
        <div id="internalConfig">Chargement...</div>
    `;

    const configDetails = document.getElementById('configDetails');
    if (configDetails) {
        configDetails.innerHTML = html;
        document.getElementById('configModal').style.display = 'block';

        if (tool === "spark" || tool === "hbase") {
            try {
                const response = await fetch(`http://localhost:8000/tools/${tool}/config`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });
                const data = await response.json();
                if (response.ok) {
                    const confHtml = Object.entries(data)
                        .map(([key, val]) => `
                            <label><strong>${key}</strong></label>
                            <input type="text" name="${key}" value="${val}" class="conf-input" style="width: 100%; margin-bottom: 10px;" />
                        `).join('');
                    document.getElementById("internalConfig").innerHTML = confHtml;

                    const applyBtn = document.createElement('button');
                    applyBtn.textContent = "Appliquer les modifications";
                    applyBtn.style.marginTop = "15px";
                    applyBtn.onclick = () => {
                        if (tool === "spark") applySparkConfig(tool);
                        if (tool === "hbase") applyHBaseConfig(tool);
                    };
                    document.getElementById("internalConfig").appendChild(applyBtn);
                } else {
                    document.getElementById("internalConfig").innerHTML = `<p style="color:red;">Erreur : ${data.detail}</p>`;
                }
            } catch (err) {
                document.getElementById("internalConfig").innerHTML = `<p style="color:red;">Erreur de requête : ${err}</p>`;
            }
        } else {
            document.getElementById("internalConfig").innerHTML = `<p>Configuration interne non disponible pour cet outil.</p>`;
        }
    }
}

async function applySparkConfig(tool) {
    const inputs = document.querySelectorAll('.conf-input');
    const newConfig = {};
    inputs.forEach(input => {
        if (input.value !== '') newConfig[input.name] = input.value;
    });

    const config = toolConfigs[tool];
    const body = { container_name: config.container_name, port: config.port, config: newConfig };

    setOutput("Application de la nouvelle configuration Spark...");

    try {
        const response = await fetch("http://localhost:8000/tools/spark/update-config", {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await response.json();

        if (response.ok) {
            setOutput("Configuration Spark mise à jour avec succès !");
            document.getElementById('configModal').style.display = 'none';
            disableConfigTemporarily(tool, 5);
        } else {
            setOutput(`Erreur : ${data.detail}`);
        }
    } catch (err) {
        setOutput(`Erreur de requête : ${err}`);
    }
}

async function applyHBaseConfig(tool) {
    const inputs = document.querySelectorAll('.conf-input');
    const newConfig = {};
    inputs.forEach(input => {
        if (input.value !== '') newConfig[input.name] = input.value;
    });

    const config = toolConfigs[tool];
    const body = { container_name: config.container_name, port: config.port, config: newConfig };

    setOutput("Application de la nouvelle configuration HBase...");

    try {
        const response = await fetch("http://localhost:8000/tools/hbase/update-config", {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await response.json();

        if (response.ok) {
            setOutput("Configuration HBase mise à jour avec succès !");
            document.getElementById('configModal').style.display = 'none';
            disableConfigTemporarily(tool, 5);
        } else {
            setOutput(`Erreur : ${data.detail}`);
        }
    } catch (err) {
        setOutput(`Erreur de requête : ${err}`);
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('customModal');
    const configModal = document.getElementById('configModal');

    const closeModalBtn = document.getElementById('closeModal');
    if (closeModalBtn) closeModalBtn.onclick = () => modal.style.display = 'none';

    const closeConfigBtn = document.getElementById('closeConfigModal');
    if (closeConfigBtn) closeConfigBtn.onclick = () => configModal.style.display = 'none';

    window.onclick = (event) => {
        if (event.target === modal) modal.style.display = 'none';
        if (event.target === configModal) configModal.style.display = 'none';
    };

    loadState();
});

// === RENDER ALL CONTAINERS WITHOUT LABELS AND STYLED TABLE ===

function renderAllContainers(containers) {
    const containerDiv = document.getElementById('allContainers');
    if (!containerDiv) return;

    if (containers.length === 0) {
        containerDiv.innerHTML = "<p>Aucun conteneur trouvé.</p>";
        return;
    }

    // Table styled with CSS class (assure-toi de l'ajouter dans style.css)
    let html = `
        <table class="containers-table">
            <thead>
                <tr>
                    <th>Nom</th>
                    <th>Image</th>
                    <th>Statut</th>
                    <th>Ports</th>
                </tr>
            </thead>
            <tbody>
    `;

    containers.forEach(c => {
        html += `
            <tr>
                <td>${c.name}</td>
                <td>${c.image}</td>
                <td>${c.status}</td>
                <td>${formatPorts(c.ports)}</td>
            </tr>
        `;
    });

    html += "</tbody></table>";
    containerDiv.innerHTML = html;
}

function formatPorts(portObj) {
    if (!portObj) return "-";
    return Object.entries(portObj)
        .map(([key, val]) => `${key} → ${val ? val.map(p => p.HostPort).join(", ") : "N/A"}`)
        .join("<br>");
}
