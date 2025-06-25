function collectSensorData() {
    console.log("🔄 Fonction collectSensorData appelée");
    
    // Test de base pour voir si la fonction est appelée
    alert("Bouton cliqué ! Début de la collecte...");
    
    // Vérification du support DeviceMotionEvent
    if (!window.DeviceMotionEvent) {
        console.error("❌ DeviceMotionEvent non supporté");
        alert("❌ DeviceMotionEvent non supporté sur cet appareil");
        return;
    }
    
    console.log("✅ DeviceMotionEvent supporté");
    
    // Test de permissions (nécessaire sur iOS 13+)
    if (DeviceMotionEvent.requestPermission) {
        console.log("🔐 Demande de permission requise (iOS)");
        DeviceMotionEvent.requestPermission().then(response => {
            console.log("🔐 Réponse permission:", response);
            if (response === 'granted') {
                startDataCollection();
            } else {
                alert("❌ Permission refusée pour les capteurs");
            }
        }).catch(error => {
            console.error("❌ Erreur permission:", error);
            alert("❌ Erreur lors de la demande de permission");
        });
    } else {
        // Pas besoin de permission (Android, desktop)
        console.log("✅ Pas de permission requise");
        startDataCollection();
    }
}

function startDataCollection() {
    console.log("🚀 Début de la collecte de données");
    
    let dataCollected = false;
    
    // Timeout de sécurité
    const timeout = setTimeout(() => {
        if (!dataCollected) {
            console.warn("⏰ Timeout - aucune donnée de capteur reçue");
            sendFallbackData();
        }
    }, 3000);
    
    const handleDeviceMotion = function(event) {
        if (dataCollected) return; // Éviter les doublons
        
        console.log("📱 Données capteur reçues:", event);
        dataCollected = true;
        clearTimeout(timeout);
        
        const data = {
            timestamp: new Date().toISOString(),
            room: getRoomFromURL(),
            accelerometer: {
                x: event.acceleration ? event.acceleration.x : null,
                y: event.acceleration ? event.acceleration.y : null,
                z: event.acceleration ? event.acceleration.z : null
            },
            gyroscope: {
                alpha: event.rotationRate ? event.rotationRate.alpha : null,
                beta: event.rotationRate ? event.rotationRate.beta : null,
                gamma: event.rotationRate ? event.rotationRate.gamma : null
            },
            magnetometer: "Not available via standard web APIs",
            wifi: "Not available via standard web APIs",
            gps: "Not available via standard web APIs",
            deviceInfo: {
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                language: navigator.language
            }
        };
        
        console.log("📦 Données à envoyer:", data);
        sendDataToServer(data);
        
        // Arrêter l'écoute après la première collecte
        window.removeEventListener('devicemotion', handleDeviceMotion);
    };
    
    window.addEventListener('devicemotion', handleDeviceMotion);
    alert("📱 Bougez légèrement votre téléphone pour activer les capteurs...");
}

function sendFallbackData() {
    console.log("🔄 Envoi de données de fallback");
    
    const data = {
        timestamp: new Date().toISOString(),
        room: getRoomFromURL(),
        accelerometer: "No motion detected",
        gyroscope: "No motion detected", 
        magnetometer: "Not available via standard web APIs",
        wifi: "Not available via standard web APIs",
        gps: "Not available via standard web APIs",
        deviceInfo: {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            language: navigator.language
        },
        note: "Fallback data - no sensor motion detected"
    };
    
    sendDataToServer(data);
}

function sendDataToServer(data) {
    console.log("🌐 Envoi vers serveur...", data);
    
    fetch('/collect_sensor_data', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    })
    .then(response => {
        console.log("📡 Réponse serveur:", response.status, response.statusText);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(result => {
        console.log("✅ Succès:", result);
        alert("✅ Données envoyées avec succès !");
    })
    .catch(error => {
        console.error("❌ Erreur:", error);
        alert("❌ Erreur lors de l'envoi: " + error.message);
    });
}

function getRoomFromURL() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('room') || 'unknown';
}

// Test de connectivité au chargement de la page
window.addEventListener('load', function() {
    console.log("🌐 Page chargée, test de connectivité...");
    
    fetch('/collect_sensor_data', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({test: true}),
    })
    .then(response => {
        console.log("✅ Serveur accessible:", response.status);
    })
    .catch(error => {
        console.error("❌ Serveur inaccessible:", error);
    });
});