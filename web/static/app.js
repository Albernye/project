// static/app.js

document.addEventListener('DOMContentLoaded', () => {
  // ——————————————————————————————
  // 1. Initialisation de la carte Leaflet (unique)
  // ——————————————————————————————
  const mapEl = document.getElementById('map');
  const initialRoom = mapEl.dataset.room;

  const map = L.map('map', {
    crs: L.CRS.EPSG4326,
    minZoom: 17,
    maxZoom: 22
  }).setView([41.406, 2.195], 19);

  const imageBounds = [
    [41.406406579820214, 2.1949513612820226],  // SW (bas gauche)
    [41.40687698399577,  2.1943470620768153]   // NE (haut droit)
  ];

  L.imageOverlay(
    '/static/OBuilding_Floor2.png',
    imageBounds,
    { opacity: 1.0 }
  ).addTo(map);
  map.fitBounds(imageBounds);

  // ensuite tu peux ajouter ton marker et routeLayer...
  const userMarker = L.marker([0, 0]).addTo(map);
  let routeLayer = null;

  // ——————————————————————————————
  // 2. Gestion des erreurs
  // ——————————————————————————————
  function handleError(err) {
    console.error(err);
  }

  // ——————————————————————————————
  // 3. Requête /position et MAJ du marqueur
  // ——————————————————————————————
  async function updatePosition() {
    try {
      const res = await fetch(`/position?room=${initialRoom}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const { position, timestamp } = await res.json();
      const [lat, lng] = position;

      userMarker.setLatLng([lat, lng]);
      document.getElementById('coordinates').textContent =
        `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
      document.getElementById('timestamp').textContent =
        new Date(timestamp).toLocaleTimeString();

      if (!map.getBounds().contains(userMarker.getLatLng())) {
        map.panTo(userMarker.getLatLng());
      }
    } catch (e) {
      handleError(e);
    }
  }

  updatePosition();
  setInterval(updatePosition, 5000);

  // ——————————————————————————————
  // 4. Calcul d’itinéraire via /route
  // ——————————————————————————————
  document.getElementById('goBtn').addEventListener('click', async () => {
    const dest = document.getElementById('destSelect').value;
    if (!dest) {
      alert('Please select a destination room');
      return;
    }
    try {
      const res = await fetch(`/route?from=${initialRoom}&to=${dest}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const geojson = await res.json();

      if (routeLayer) map.removeLayer(routeLayer);
      routeLayer = L.geoJSON(geojson, {
        style: { color: 'blue', weight: 4 }
      }).addTo(map);

      map.fitBounds(routeLayer.getBounds());
    } catch (e) {
      handleError(e);
      alert('Route not found');
    }
  });

  // ——————————————————————————————
  // 5. Recalibration via /confirm_position
  // ——————————————————————————————
  document.getElementById('recalibrate').addEventListener('click', async () => {
    try {
      await fetch('/confirm_position', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          room: initialRoom,
          position: userMarker.getLatLng()
        })
      });
      alert('Position recalibrated');
    } catch (e) {
      handleError(e);
      alert('Recalibration failed');
    }
  });

  // ——————————————————————————————
  // 6. Collecte de données capteurs (DeviceMotion)
  // ——————————————————————————————
  window.collectSensorData = () => {
    console.log('🔄 Starting sensor data collection');
    // Visuel de statut
    const statusDiv = document.createElement('div');
    statusDiv.id = 'sensor-status';
    Object.assign(statusDiv.style, {
      position: 'fixed', top: '20px', right: '20px',
      padding: '10px', background: 'rgba(0,0,0,0.8)',
      color: 'white', borderRadius: '8px'
    });
    document.body.appendChild(statusDiv);
    const updateStatus = (msg, color='white') => {
      statusDiv.textContent = `📡 ${msg}`;
      statusDiv.style.color = color;
    };

    if (!window.DeviceMotionEvent) {
      updateStatus('DeviceMotion not supported', 'red');
      return;
    }
    updateStatus('Requesting sensor permission...');
    const startDataCollection = () => {
      updateStatus('Collecting sensor data...', '#4CAF50');
      let dataSent = false;
      const timeout = setTimeout(() => {
        if (!dataSent) {
          updateStatus('No data → sending fallback', 'orange');
          sendData({ test: true, room: initialRoom, note: 'fallback' });
        }
      }, 3000);

      const onMotion = event => {
        if (dataSent) return;
        dataSent = true;
        clearTimeout(timeout);
        const payload = {
          timestamp: new Date().toISOString(),
          room: initialRoom,
          accelerometer: {
            x: event.acceleration?.x,
            y: event.acceleration?.y,
            z: event.acceleration?.z
          },
          gyroscope: {
            alpha: event.rotationRate?.alpha,
            beta: event.rotationRate?.beta,
            gamma: event.rotationRate?.gamma
          },
          deviceInfo: {
            ua: navigator.userAgent,
            platform: navigator.platform
          }
        };
        updateStatus('Sending data...', '#2196F3');
        sendData(payload);
        window.removeEventListener('devicemotion', onMotion);
      };

      window.addEventListener('devicemotion', onMotion);
    };

    if (typeof DeviceMotionEvent.requestPermission === 'function') {
      DeviceMotionEvent.requestPermission()
        .then(r => (r==='granted' ? startDataCollection() : updateStatus('Permission denied','red')))
        .catch(e => { handleError(e); updateStatus('Permission error','red'); });
    } else {
      startDataCollection();
    }
  };

  function sendData(data) {
    fetch('/collect_sensor_data', {
      method: 'POST',
      headers: { 'Content-Type':'application/json' },
      body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(json => {
      console.log('Sensor data response:', json);
      alert('Sensor data sent');
    })
    .catch(handleError);
  }
});
