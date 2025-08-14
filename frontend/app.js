let currentTool = null;
let runningTools = [];
let toolConfigs = {};

// Sauvegarde la config dans localStorage
function saveState() {
    localStorage.setItem('toolConfigs', JSON.stringify(toolConfigs));
}

// Charge la config depuis localStorage et récupère la liste des conteneurs côté backend
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

// Détecte le type d'outil depuis le nom du conteneur
function detectToolFromName(name) {
    name = name.toLowerCase();
    if (name.includes("spark")) return "spark";
    if (name.includes("hbase")) return "hbase";
    if (name.includes("mongo")) return "mongodb";
    return null;
}

// Affiche un message dans la zone output
function setOutput(msg) {
    const outputEl = document.getElementById('output');
    if (outputEl) outputEl.textContent = msg;
}

// Met à jour le statut d'un outil (running ou non) dans l'interface et dans les listes
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

// Met à jour la liste des outils en cours dans l'interface avec boutons de configuration et compteurs
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

// Désactive temporairement le bouton config avec un compte à rebours (seconds)
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

// Affiche la modal de personnalisation de démarrage
async function startTool(tool) {
    showCustomizeModal(tool);
}

// Arrête un outil en envoyant la config au backend
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
            setOutput(`Erreur : ${data.detail || `Échec de l'arrêt de ${tool}`}`);
        }
    } catch (err) {
        setOutput(`Erreur : ${err}`);
    }
}

// Affiche la modal de personnalisation avec la config sauvegardée
function showCustomizeModal(tool) {
    currentTool = tool;
    const el = document.getElementById('customToolName');
    if (el) el.textContent = tool.charAt(0).toUpperCase() + tool.slice(1);

    const config = toolConfigs[tool] || {};
    document.getElementById('container_name').value = config.container_name || '';
    document.getElementById('username').value = config.username || '';
    document.getElementById('password').value = config.password || '';
    document.getElementById('port').value = config.port || '8080';

    document.getElementById('customModal').style.display = 'block';
}

// Soumet la configuration personnalisée et démarre l'outil via API
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
            setOutput(`Erreur : ${data.detail || `Échec du démarrage de ${currentTool}`}`);
        }
    } catch (err) {
        setOutput(`Erreur : ${err}`);
    }
}

// Affiche la modal de configuration interne avec possibilité de modification (pour Spark et HBase et mongodb )
async function showConfigModal(tool) {
    const config = toolConfigs[tool];
    if (!config) {
        alert("Configuration non disponible !");
        return;
    }

    // Affichage infos Docker de base
    const html = `
        <h3>Configuration Docker</h3>
        <p><strong>Outil :</strong> ${tool.charAt(0).toUpperCase() + tool.slice(1)}</p>
        <p><strong>Nom du conteneur :</strong> ${config.container_name || ""}</p>
        <p><strong>Nom d'utilisateur :</strong> ${config.username || ""}</p>
        <p><strong>Mot de passe :</strong> ${config.password || ""}</p>
        <p><strong>Port :</strong> ${config.port || ""}</p>
        <hr>
        <h3>Configuration Interne</h3>
        <div id="internalConfig">Chargement...</div>
    `;

    const configDetails = document.getElementById('configDetails');
    if (!configDetails) return;
    configDetails.innerHTML = html;
    document.getElementById('configModal').style.display = 'block';

    try {
        const response = await fetch(`http://localhost:8000/tools/${tool}/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        const data = await response.json();

        if (!response.ok) {
            document.getElementById("internalConfig").innerHTML = `<p style="color:red;">Erreur : ${data.detail || 'Unknown error'}</p>`;
            return;
        }

        if (tool === "mongodb") {
            // Normaliser la config reçue
            const conf = data.config || data;

            // Génération formulaire MongoDB (ports + env + autres)
            let formHtml = '';

            // Ports
            if (conf.ports) {
                formHtml += `<h4>Ports exposés :</h4><div id="portsContainer">`;
                for (const [portKey, portVal] of Object.entries(conf.ports)) {
                    const hostPorts = portVal ? portVal.map(p => p.HostPort).join(", ") : "";
                    formHtml += `
                        <label><strong>${portKey}</strong></label><br/>
                        <input type="text" name="ports[${portKey}]" value="${hostPorts}" style="width: 100%; margin-bottom: 10px;" />
                    `;
                }
                formHtml += `</div>`;
            }

            // Env variables
            if (conf.env) {
                formHtml += `<h4>Variables d'environnement :</h4><div id="envContainer">`;
                for (const [envKey, envVal] of Object.entries(conf.env)) {
                    formHtml += `
                        <label><strong>${envKey}</strong></label><br/>
                        <input type="text" name="env[${envKey}]" value="${envVal}" style="width: 100%; margin-bottom: 10px;" />
                    `;
                }
                formHtml += `</div>`;
            }

            // Autres champs simples (exclure ports/env)
            for (const [key, value] of Object.entries(conf)) {
                if (key !== "ports" && key !== "env" && (typeof value !== 'object' || value === null)) {
                    formHtml += `
                        <label><strong>${key}</strong></label><br/>
                        <input type="text" name="${key}" value="${value || ""}" style="width: 100%; margin-bottom: 10px;" />
                    `;
                }
            }

            formHtml += `<button id="applyMongoConfigBtn" style="margin-top: 15px;">Appliquer les modifications</button>`;

            document.getElementById("internalConfig").innerHTML = formHtml;

            // Bouton appliquer
            document.getElementById("applyMongoConfigBtn").onclick = async () => {
                // Récup ports
                const portsInputs = document.querySelectorAll('#portsContainer input');
                const newPorts = {};
                portsInputs.forEach(input => {
                    const key = input.name.match(/ports\[(.+)\]/)[1];
                    const hostPorts = input.value.split(',').map(p => p.trim()).filter(p => p !== "");
                    newPorts[key] = hostPorts.map(port => ({ HostPort: port }));
                });

                // Récup env
                const envInputs = document.querySelectorAll('#envContainer input');
                const newEnv = {};
                envInputs.forEach(input => {
                    const key = input.name.match(/env\[(.+)\]/)[1];
                    newEnv[key] = input.value;
                });

                // Récup autres inputs simples hors ports/env
                const otherInputs = Array.from(document.querySelectorAll('#internalConfig > input:not([name^="ports["]):not([name^="env["])'));
                const otherConfig = {};
                otherInputs.forEach(input => {
                    otherConfig[input.name] = input.value;
                });

                const body = {
                    container_name: config.container_name,
                    port: config.port,
                    config: {
                        ...otherConfig,
                        ports: newPorts,
                        env: newEnv
                    }
                };

                setOutput("Application de la nouvelle configuration MongoDB...");

                try {
                    const respUpdate = await fetch("http://localhost:8000/tools/mongodb/update-config", {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(body)
                    });
                    const dataUpdate = await respUpdate.json();

                    if (respUpdate.ok) {
                        setOutput("Configuration MongoDB mise à jour avec succès !");
                        document.getElementById('configModal').style.display = 'none';
                        disableConfigTemporarily(tool, 5);
                    } else {
                        setOutput(`Erreur : ${dataUpdate.detail || 'Erreur inconnue'}`);
                    }
                } catch (err) {
                    setOutput(`Erreur de requête : ${err}`);
                }
            };

        } else if (tool === "spark" || tool === "hbase") {
            // Formulaire simple pour spark et hbase
            const confHtml = Object.entries(data)
                .map(([key, val]) => `
                    <label><strong>${key}</strong></label>
                    <input type="text" name="${key}" value="${val || ""}" class="conf-input" style="width: 100%; margin-bottom: 10px;" />
                `).join('');
            document.getElementById("internalConfig").innerHTML = confHtml;

            const applyBtn = document.createElement('button');
            applyBtn.textContent = "Appliquer les modifications";
            applyBtn.style.marginTop = "15px";
            applyBtn.onclick = () => {
                if (tool === "spark") applySparkConfig(tool);
                else if (tool === "hbase") applyHBaseConfig(tool);
            };
            document.getElementById("internalConfig").appendChild(applyBtn);

        } else {
            // Autres outils : affichage JSON brut
            document.getElementById("internalConfig").innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        }
    } catch (err) {
        document.getElementById("internalConfig").innerHTML = `<p style="color:red;">Erreur de requête : ${err}</p>`;
    }
}

// Applique la configuration modifiée pour Spark
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

// Applique la configuration modifiée pour HBase
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

// Au chargement de la page : gestion des modals et chargement des états
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

// Affiche la liste complète des conteneurs dans un tableau
function renderAllContainers(containers) {
    const containerDiv = document.getElementById('allContainers');
    if (!containerDiv) return;

    if (containers.length === 0) {
        containerDiv.innerHTML = "<p>Aucun conteneur trouvé.</p>";
        return;
    }

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

// Formate les ports pour affichage lisible
function formatPorts(portObj) {
    if (!portObj) return "-";
    return Object.entries(portObj)
        .map(([key, val]) => `${key} → ${val ? val.map(p => p.HostPort).join(", ") : "N/A"}`)
        .join("<br>");
}


async function applyMongoConfig(tool) {
    // Récupérer la config actuelle
    const config = toolConfigs[tool];
    if (!config) {
        setOutput("Configuration MongoDB introuvable.");
        return;
    }

    // Récupérer les valeurs modifiées du formulaire
    const internalConfigDiv = document.getElementById("internalConfig");
    if (!internalConfigDiv) return;

    const inputs = internalConfigDiv.querySelectorAll("input");
    const newPorts = {};
    const newEnv = {};

    inputs.forEach(input => {
        const name = input.name;
        const value = input.value.trim();

        if (name.startsWith("ports-")) {
            const portKey = name.slice(6);
            // Convertir la chaîne en tableau (séparé par virgule)
            const portsArray = value ? value.split(",").map(p => p.trim()).filter(p => p !== "") : [];
            // Construire un tableau d'objets { HostPort: port }
            newPorts[portKey] = portsArray.map(p => ({ HostPort: p }));
        } else if (name.startsWith("env-")) {
            const envKey = name.slice(4);
            newEnv[envKey] = value;
        }
    });

    const body = {
        container_name: config.container_name,
        port: config.port,
        config: {
            ports: newPorts,
            env: newEnv
        }
    };

    setOutput("Application de la nouvelle configuration MongoDB...");

    try {
        const response = await fetch("http://localhost:8000/tools/mongodb/update-config", {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        const data = await response.json();

        if (response.ok) {
            setOutput("Configuration MongoDB mise à jour avec succès !");
            document.getElementById('configModal').style.display = 'none';
            disableConfigTemporarily(tool, 5);
        } else {
            setOutput(`Erreur : ${data.detail || "Échec de la mise à jour"}`);
        }
    } catch (err) {
        setOutput(`Erreur de requête : ${err}`);
    }
}
