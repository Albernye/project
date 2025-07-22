document.addEventListener('DOMContentLoaded', () => {
  console.log("=== DÉBUT INITIALISATION APP ===");
  
  // ——————————————————————————————
  // 1. DIAGNOSTIC COMPLET
  // ——————————————————————————————
  
  // Vérifier que Leaflet est chargé
  if (typeof L === 'undefined') {
    console.error("❌ ERREUR CRITIQUE: Leaflet n'est pas chargé!");
    alert("Leaflet non chargé. Vérifiez votre connexion internet.");
    return;
  }
  console.log("✅ Leaflet chargé:", L.version);

  // Vérifier l'élément map
  const mapEl = document.getElementById('map');
  if (!mapEl) {
    console.error("❌ ERREUR CRITIQUE: Élément #map introuvable!");
    return;
  }
  console.log("✅ Élément map trouvé:", mapEl);
  
  // Vérifier les dimensions de l'élément map
  const mapRect = mapEl.getBoundingClientRect();
  console.log("📐 Dimensions map:", {
    width: mapRect.width,
    height: mapRect.height,
    top: mapRect.top,
    left: mapRect.left
  });
  
  if (mapRect.width === 0 || mapRect.height === 0) {
    console.error("❌ ERREUR: La carte a des dimensions nulles!");
    console.log("🔍 Styles appliqués:", window.getComputedStyle(mapEl));
  }

  const initialRoom = mapEl.dataset.room;
  console.log("🏠 Room initiale:", initialRoom);

  // ——————————————————————————————
  // 2. INITIALISATION CARTE STEP BY STEP
  // ——————————————————————————————
  
  let map;
  
  try {
    console.log("🗺️ Création de l'instance Leaflet...");
    
    map = L.map('map', {
      crs: L.CRS.EPSG4326,
      minZoom: 0,
      maxZoom: 4,
      zoomControl: true,
      attributionControl: false
    });
    console.log("✅ Instance Leaflet créée");

    // Utiliser les bounds calibrés directement
    // Configuration du système de coordonnées simple (pixels)
    map.options.crs = L.CRS.Simple;
    
    // Dimensions de l'image en pixels
    const imgWidth = 2556;
    const imgHeight = 816;
    
    // Définir les bounds [sud-ouest, nord-est] en y,x
    const southWest = map.unproject([0, imgHeight], 0);
    const northEast = map.unproject([imgWidth, 0], 0);
    const mapBounds = new L.LatLngBounds(southWest, northEast);
    
    // Ajouter l'image overlay avec les bons bounds
    L.imageOverlay(
      '/static/OBuilding_Floor2.png',
      mapBounds,
      { 
        opacity: 1.0,
        interactive: false,
        crossOrigin: false
      }
    ).addTo(map)
      .on('load', () => console.log("✅ Image overlay chargée avec succès"))
      .on('error', (e) => console.error("❌ Erreur chargement image overlay:", e));
    
    // Définir la vue et les limites
    map.setView(mapBounds.getCenter(), 1);
    map.setMaxBounds(mapBounds);
    console.log("✅ Configuration CRS Simple avec dimensions réelles");
    
    // Forcer le redimensionnement après un délai
    setTimeout(() => {
      console.log("🔄 Invalidation taille carte...");
      map.invalidateSize();
      console.log("✅ Taille carte invalidée");
    }, 250);

  } catch (error) {
    console.error("❌ ERREUR lors de l'initialisation carte:", error);
    alert(`Erreur carte: ${error.message}`);
    return;
  }

  // ——————————————————————————————
  // 3. MARQUEUR UTILISATEUR
  // ——————————————————————————————
  
  console.log("📌 Ajout marqueur utilisateur...");
  const userMarker = L.marker([41.406368, 2.175568], {
    title: 'Votre position',
    draggable: false
  }).addTo(map);
  console.log("✅ Marqueur utilisateur ajouté");

  let routeLayer = null;

  // ——————————————————————————————
  // 4. FONCTIONS UTILITAIRES
  // ——————————————————————————————
  
  function handleError(err) {
    console.error("🚨 Erreur application:", err);
    
    // Affichage d'erreur plus discret mais visible
    const toast = document.createElement('div');
    toast.style.cssText = `
      position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
      background: #ff4444; color: white; padding: 12px 20px;
      border-radius: 6px; z-index: 10000; font-size: 14px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    `;
    toast.textContent = `Erreur: ${err.message || err}`;
    document.body.appendChild(toast);
    
    setTimeout(() => {
      if (toast.parentNode) toast.remove();
    }, 5000);
  }

  function showStatus(message, color = '#333') {
    console.log("📢 Status:", message);
    const statusEl = document.getElementById('coordinates');
    if (statusEl) {
      const originalText = statusEl.textContent;
      statusEl.style.color = color;
      statusEl.textContent = message;
      setTimeout(() => {
        statusEl.style.color = '';
        if (statusEl.textContent === message) {
          statusEl.textContent = originalText;
        }
      }, 3000);
    }
  }

  // ——————————————————————————————
  // 5. MISE À JOUR POSITION
  // ——————————————————————————————
  
  async function updatePosition() {
    try {
      console.log("🔄 Mise à jour position...");
      showStatus("Mise à jour...", "#007AFF");
      
      const res = await fetch(`/position?room=${initialRoom}`);
      if (!res.ok) {
        throw new Error(`Erreur serveur: ${res.status} ${res.statusText}`);
      }
      
      const data = await res.json();
      console.log("📡 Données reçues:", data);
      
      const { position, timestamp } = data;
      const [lng, lat] = position;

      // Mettre à jour le marqueur
      userMarker.setLatLng([lat, lng]);
      
      // Mettre à jour l'interface
      const coordsEl = document.getElementById('coordinates');
      const timestampEl = document.getElementById('timestamp');
      
      if (coordsEl) {
        coordsEl.textContent = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
        coordsEl.style.color = '#4CAF50';
      }
      if (timestampEl) {
        timestampEl.textContent = new Date(timestamp).toLocaleTimeString();
      }

      // Centrer si nécessaire
      if (!map.getBounds().contains([lat, lng])) {
        map.setView([lat, lng], map.getZoom());
      }
      
      console.log("✅ Position mise à jour:", lat, lng);
      
    } catch (error) {
      console.error("❌ Erreur mise à jour position:", error);
      showStatus("Erreur position", "#ff4444");
      handleError(error);
    }
  }

  // ——————————————————————————————
  // 6. GESTION BOUTONS
  // ——————————————————————————————
  
  // Bouton Route
  const goBtn = document.getElementById('goBtn');
  if (goBtn) {
    goBtn.addEventListener('click', async () => {
      const destSelect = document.getElementById('destSelect');
      const dest = destSelect?.value;
    
    if (!dest) {
      alert('Veuillez sélectionner une destination');
      return;
    }
    
    try {
      goBtn.disabled = true;
      goBtn.textContent = 'Calcul...';
      showStatus("Calcul itinéraire...", "#007AFF");
      
      const res = await fetch(`/route?from=${initialRoom}&to=${dest}`);
      if (!res.ok) throw new Error(`Erreur route: ${res.status}`);
      
      const geojson = await res.json();
      console.log("🛤️ GeoJSON reçu:", geojson);

      // Supprimer l'ancienne route
      if (routeLayer) {
        map.removeLayer(routeLayer);
      }
      
      // Ajouter la nouvelle route
      routeLayer = L.geoJSON(geojson, {
        style: { 
          color: '#007AFF', 
          weight: 4, 
          opacity: 0.8,
          dashArray: '10, 5'
        }
      }).addTo(map);

      // S'assurer que la route est devant l'image
      routeLayer.bringToFront();
      // ou alternativement :
      // imageOverlay.bringToBack();

      // Centrer la vue sur le centre de la route, sans toucher au zoom
      const routeCenter = routeLayer.getBounds().getCenter();
      map.setView(routeCenter, map.getZoom());

      showStatus("Itinéraire calculé", "#4CAF50");
      console.log("✅ Itinéraire affiché");
      
    } catch (error) {
      console.error("❌ Erreur calcul route:", error);
      showStatus("Erreur itinéraire", "#ff4444");
      alert('Impossible de calculer l\'itinéraire');
    } finally {
      goBtn.disabled = false;
      goBtn.textContent = 'Route';
    }
  });
} else {
  console.warn("⚠️ Bouton 'goBtn' introuvable");
}


  // Bouton Recalibrage
  const recalibrateBtn = document.getElementById('recalibrate');
  if (recalibrateBtn) {
    recalibrateBtn.addEventListener('click', async () => {
      try {
        recalibrateBtn.disabled = true;
        recalibrateBtn.textContent = 'Recalibrage...';
        showStatus("Recalibrage...", "#FF9500");
        
        const currentPos = userMarker.getLatLng();
        const response = await fetch('/confirm_position', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            room: initialRoom,
            position: [currentPos.lat, currentPos.lng]
          })
        });
        
        if (!response.ok) throw new Error(`Erreur: ${response.status}`);
        
        showStatus("Position recalibrée", "#4CAF50");
        console.log("✅ Recalibrage effectué");
        
      } catch (error) {
        console.error("❌ Erreur recalibrage:", error);
        showStatus("Erreur recalibrage", "#ff4444");
        handleError(error);
      } finally {
        recalibrateBtn.disabled = false;
        recalibrateBtn.textContent = 'Recalibrate';
      }
    });
  } else {
    console.warn("⚠️ Bouton 'recalibrate' introuvable");
  }

  // ——————————————————————————————
  // 7. COLLECTE CAPTEURS (Multi-plateforme)
  // ——————————————————————————————
  
  window.collectSensorData = async () => {
    console.log('🔄 Démarrage collecte capteurs...');
    
    const statusDiv = document.createElement('div');
    statusDiv.id = 'sensor-status';
    statusDiv.style.cssText = `
      position: fixed; top: 20px; right: 20px; z-index: 10000;
      background: rgba(0,0,0,0.9); color: white; padding: 12px;
      border-radius: 6px; font-size: 14px; max-width: 250px;
    `;
    document.body.appendChild(statusDiv);
    
    const updateStatus = (msg, color = 'white') => {
      statusDiv.textContent = `📱 ${msg}`;
      statusDiv.style.color = color;
    };

    // Détection du type d'appareil
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    const isAndroid = /Android/.test(navigator.userAgent);
    const isMobile = isIOS || isAndroid || /Mobile/.test(navigator.userAgent);
    
    console.log('📱 Plateforme détectée:', { isIOS, isAndroid, isMobile });
    updateStatus(`Plateforme: ${isIOS ? 'iOS' : isAndroid ? 'Android' : 'Desktop'}`);

    if (!window.DeviceMotionEvent) {
      updateStatus('Capteurs non disponibles', 'orange');
      setTimeout(() => statusDiv.remove(), 3000);
      return;
    }

    // Fonction de collecte universelle
    const collectData = () => {
      updateStatus('Collecte en cours...', '#4CAF50');
      let collected = false;
      
      const timeout = setTimeout(() => {
        if (!collected) {
          updateStatus('Timeout - envoi données test', 'orange');
          sendSensorData({
            test: true,
            room: initialRoom,
            platform: { isIOS, isAndroid, isMobile },
            timestamp: new Date().toISOString()
          });
          collected = true;
        }
      }, 2000);

      const handleMotion = (event) => {
        if (collected) return;
        collected = true;
        clearTimeout(timeout);
        
        const sensorData = {
          timestamp: new Date().toISOString(),
          room: initialRoom,
          platform: { isIOS, isAndroid, isMobile },
          accelerometer: {
            x: event.acceleration?.x || null,
            y: event.acceleration?.y || null,
            z: event.acceleration?.z || null
          },
          gyroscope: {
            alpha: event.rotationRate?.alpha || null,
            beta: event.rotationRate?.beta || null,
            gamma: event.rotationRate?.gamma || null
          },
          accelerationIncludingGravity: {
            x: event.accelerationIncludingGravity?.x || null,
            y: event.accelerationIncludingGravity?.y || null,
            z: event.accelerationIncludingGravity?.z || null
          },
          deviceInfo: {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            language: navigator.language,
            screen: `${screen.width}x${screen.height}`
          }
        };
        
        updateStatus('Envoi données...', '#2196F3');
        sendSensorData(sensorData);
        window.removeEventListener('devicemotion', handleMotion);
      };

      window.addEventListener('devicemotion', handleMotion);
    };

    // Gestion des permissions iOS
    if (isIOS && typeof DeviceMotionEvent.requestPermission === 'function') {
      updateStatus('Demande permission iOS...', '#FF9500');
      try {
        const permission = await DeviceMotionEvent.requestPermission();
        if (permission === 'granted') {
          collectData();
        } else {
          updateStatus('Permission refusée', 'red');
          setTimeout(() => statusDiv.remove(), 3000);
        }
      } catch (error) {
        console.error('Erreur permission iOS:', error);
        updateStatus('Erreur permission', 'red');
        setTimeout(() => statusDiv.remove(), 3000);
      }
    } else {
      // Android et autres plateformes
      collectData();
    }
  };

  async function sendSensorData(data) {
    try {
      const response = await fetch('/collect_sensor_data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      
      const statusDiv = document.getElementById('sensor-status');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      const result = await response.json();
      console.log('✅ Données capteurs envoyées:', result);
      
      if (statusDiv) {
        statusDiv.textContent = '✅ Données envoyées';
        statusDiv.style.color = '#4CAF50';
        setTimeout(() => statusDiv.remove(), 2000);
      }
      
    } catch (error) {
      console.error('❌ Erreur envoi capteurs:', error);
      const statusDiv = document.getElementById('sensor-status');
      if (statusDiv) {
        statusDiv.textContent = '❌ Erreur envoi';
        statusDiv.style.color = 'red';
        setTimeout(() => statusDiv.remove(), 3000);
      }
    }
  }

  // ——————————————————————————————
  // 8. DÉMARRAGE ET ÉVÉNEMENTS
  // ——————————————————————————————
  
  // Première mise à jour après un délai
  setTimeout(updatePosition, 1000);
  
  // Mise à jour périodique
  const updateInterval = setInterval(updatePosition, 5000);
  
  // Gestion redimensionnement
  const handleResize = () => {
    console.log("🔄 Redimensionnement détecté");
    setTimeout(() => {
      if (map) {
        map.invalidateSize();
        const imageBounds = [
          [41.406406579820214, 2.1949513612820226],
          [41.40687698399577, 2.1943470620768153]
        ];
        map.fitBounds(imageBounds);
      }
    }, 100);
  };
  
  window.addEventListener('resize', handleResize);
  window.addEventListener('orientationchange', () => {
    setTimeout(handleResize, 300);
  });
  
  // Gestion visibilité page
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && map) {
      setTimeout(() => map.invalidateSize(), 100);
    }
  });

  console.log("✅ === INITIALISATION APP TERMINÉE ===");
  showStatus("Application prête", "#4CAF50");
});
