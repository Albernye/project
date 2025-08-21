document.addEventListener('DOMContentLoaded', () => {
  console.log("=== BEGINNING APP INITIALIZATION ===");

  // ——————————————————————————————
  // 1. GLOBAL VARIABLES AND CONFIGURATION
  // ——————————————————————————————

  let map;
  let userMarker;
  let routeLayer = null;
  let pollingInterval = null;
  let currentRoom;
  let lastPolledRoom;

  // Map configuration constants
  const MAP_CONFIG = {
    IMAGE_WIDTH: 2556,
    IMAGE_HEIGHT: 816,
    IMAGE_PATH: '/static/OBuilding_Floor2.png',
    DEFAULT_ZOOM: 1,
    MAX_ZOOM: 4,
    MIN_ZOOM: 0,
    UPDATE_INTERVAL: 5000, // 5 seconds
    ANIMATION_STEPS: 10
  };

  // ——————————————————————————————
  // 2. COORDINATE TRANSFORMATION FUNCTIONS
  // ——————————————————————————————

  /**
   * Convert GPS coordinates to pixel coordinates for the building map
   * @param {number} lon - Longitude (GPS)
   * @param {number} lat - Latitude (GPS)
   * @returns {array} [x, y] pixel coordinates
   */
  function gpsToPixel(lon, lat) {
    const GPS_BOUNDS = {
        minLon: 2.175568,  // Room 2-01
        maxLon: 2.194291,  // Room 2-13  
        minLat: 41.406315, // Room 2-19
        maxLat: 41.406369  // Rooms 2-06, 2-07, etc.
    };
    
    const x_raw = MAP_CONFIG.IMAGE_WIDTH - ((lon - GPS_BOUNDS.minLon) / (GPS_BOUNDS.maxLon - GPS_BOUNDS.minLon)) * MAP_CONFIG.IMAGE_WIDTH;
    const y_raw = ((lat - GPS_BOUNDS.minLat) / (GPS_BOUNDS.maxLat - GPS_BOUNDS.minLat)) * MAP_CONFIG.IMAGE_HEIGHT;

    // OFFSET and SCALE :
    const X_OFFSET = -150; // Offset in pixels (to adjust)
    const X_SCALE_FACTOR = 1; // Reduce the horizontal scale (to adjust)
    const Y_SCALE_FACTOR = 0.1; // Reduce the vertical scale (to adjust)
    const Y_OFFSET = 500;       // Offset in pixels (to adjust)

    const x = x_raw * X_SCALE_FACTOR + X_OFFSET;
    const y = y_raw * Y_SCALE_FACTOR + Y_OFFSET;
    return [x, y];
}

  /**
   * Convert pixel coordinates to Leaflet LatLng for Simple CRS
   * @param {number} x - X pixel coordinate
   * @param {number} y - Y pixel coordinate
   * @returns {L.LatLng} Leaflet coordinate
   */
  function pixelToLeaflet(x, y) {
    return map.unproject([x, y], 0);
  }

  /**
   * Convert GPS coordinates directly to Leaflet coordinates
   * @param {number} lon - GPS longitude
   * @param {number} lat - GPS latitude
   * @returns {L.LatLng} Leaflet coordinate
   */
  function gpsToLeaflet(lon, lat) {
    const [x, y] = gpsToPixel(lon, lat);
    return pixelToLeaflet(x, y);
  }

  // ——————————————————————————————
  // 3. ROOM DETECTION AND URL MANAGEMENT
  // ——————————————————————————————

  function getRoomFromURL() {
    const urlParams = new URLSearchParams(window.location.search);
    const room = urlParams.get('room');
    const mapEl = document.getElementById('map');
    return room ? room : (mapEl ? mapEl.dataset.room : null);
  }

  /**
   * Initialize room tracking from URL
   */
  function initializeRoom() {
    currentRoom = getRoomFromURL();
    lastPolledRoom = currentRoom;
    console.log("🏠 Initial room:", currentRoom);
  }

  /**
   * Check for room changes in URL and restart polling if needed
   */
  function checkRoomChangeAndUpdatePolling() {
    const newRoom = getRoomFromURL();
    if (newRoom !== lastPolledRoom) {
      console.log('🔄 Room changed from', lastPolledRoom, 'to', newRoom);
      currentRoom = newRoom;
      lastPolledRoom = newRoom;

      // Writing a new room change event
      fetch('/change_room', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room: newRoom })
      })
      .then(res => res.json())
      .then(data => {
        console.log('✅ QR event written for room:', data.room);
        if (pollingInterval) {
          clearInterval(pollingInterval);
        }
        // Immediate position update and restart polling
        updatePosition(false);
        pollingInterval = setInterval(() => updatePosition(true), MAP_CONFIG.UPDATE_INTERVAL);
        console.log('🔄 Polling restarted for room:', currentRoom);
      })
      .catch(err => {
        console.error('❌ Error writing QR event:', err);
        handleError(err);
      });
    }
  }

  // ——————————————————————————————
  // 4. DIAGNOSTIC AND VALIDATION
  // ——————————————————————————————

  /**
   * Verify that all required dependencies are loaded
   * @returns {boolean} True if all dependencies are available
   */
  function validateDependencies() {
    // Verify Leaflet is loaded
    if (typeof L === 'undefined') {
      console.error("❌ CRITICAL ERROR: Leaflet is not loaded!");
      alert("Leaflet not loaded. Please check your internet connection.");
      return false;
    }
    console.log("✅ Leaflet loaded:", L.version);

    // Verify map element exists
    const mapEl = document.getElementById('map');
    if (!mapEl) {
      console.error("❌ CRITICAL ERROR: Element #map not found!");
      return false;
    }
    console.log("✅ Map element found:", mapEl);

    // Check map element dimensions
    const mapRect = mapEl.getBoundingClientRect();
    console.log("📐 Map dimensions:", {
      width: mapRect.width,
      height: mapRect.height,
      top: mapRect.top,
      left: mapRect.left
    });
    
    if (mapRect.width === 0 || mapRect.height === 0) {
      console.error("❌ ERROR: Map has zero dimensions!");
      console.log("🔍 Applied styles:", window.getComputedStyle(mapEl));
    }

    return true;
  }

  // ——————————————————————————————
  // 5. MAP INITIALIZATION
  // ——————————————————————————————

  /**
   * Initialize Leaflet map with custom coordinate system
   * @returns {boolean} True if initialization successful
   */
  function initializeMap() {
    try {
      console.log("Creating Leaflet map instance...");

      map = L.map('map', {
        crs: L.CRS.Simple,
        minZoom: MAP_CONFIG.MIN_ZOOM,
        maxZoom: MAP_CONFIG.MAX_ZOOM,
        zoomControl: true,
        attributionControl: false
      });

      console.log("✅ Leaflet map instance created");

      // Calculate bounds for the image overlay
      const southWest = map.unproject([0, MAP_CONFIG.IMAGE_HEIGHT], 0);
      const northEast = map.unproject([MAP_CONFIG.IMAGE_WIDTH, 0], 0);
      const mapBounds = new L.LatLngBounds(southWest, northEast);

      // Add building floor plan as image overlay
      L.imageOverlay(MAP_CONFIG.IMAGE_PATH, mapBounds, {
        opacity: 1.0,
        interactive: false,
        crossOrigin: false
      })
      .addTo(map)
      .on('load', () => console.log("✅ Building floor plan loaded successfully"))
      .on('error', (e) => console.error("❌ Error loading floor plan:", e));

      // Set initial view and bounds
      map.setView(mapBounds.getCenter(), MAP_CONFIG.DEFAULT_ZOOM);
      map.setMaxBounds(mapBounds);

      console.log("✅ Map configured with Simple CRS and real dimensions");

      // Force map size recalculation after DOM is ready
      setTimeout(() => {
        console.log("Recalculating map size...");
        map.invalidateSize();
        console.log("✅ Map size recalculated");
      }, 250);

      return true;

    } catch (error) {
      console.error("❌ ERROR during map initialization:", error);
      alert(`Map initialization error: ${error.message}`);
      return false;
    }
  }

  /**
   * Add user position marker to the map
   */
  function initializeUserMarker() {
    console.log("📌 Adding user position marker...");
    
    // Position par défaut convertie en coordonnées Leaflet
    const defaultLeafletPos = gpsToLeaflet(2.175568, 41.406368);
    
    userMarker = L.marker(defaultLeafletPos, {
      title: 'Your current position',
      draggable: false
    }).addTo(map);
    
    console.log("✅ User marker added to map");
  }

  // ——————————————————————————————
  // 6. UTILITY FUNCTIONS
  // ——————————————————————————————

  /**
   * Display error messages to the user in a non-intrusive way
   * @param {Error|string} err - Error object or message
   */
  function handleError(err) {
    console.error("🚨 Application error:", err);

    // Create temporary error toast notification
    const toast = document.createElement('div');
    toast.style.cssText = `
      position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
      background: #ff4444; color: white; padding: 12px 20px;
      border-radius: 6px; z-index: 10000; font-size: 14px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      max-width: 300px; text-align: center;
    `;
    toast.textContent = `Error: ${err.message || err}`;
    document.body.appendChild(toast);
    
    // Auto-remove toast after 5 seconds
    setTimeout(() => {
      if (toast.parentNode) toast.remove();
    }, 5000);
  }

  /**
   * Show status messages in the coordinates display
   * @param {string} message - Status message to display
   * @param {string} color - CSS color for the message
   */
  function showStatus(message, color = '#333') {
    console.log("📢 Status:", message);
    const statusEl = document.getElementById('coordinates');
    
    if (statusEl) {
      const originalText = statusEl.textContent;
      statusEl.style.color = color;
      statusEl.textContent = message;
      
      // Restore original content after 3 seconds
      setTimeout(() => {
        statusEl.style.color = '';
        if (statusEl.textContent === message) {
          statusEl.textContent = originalText;
        }
      }, 3000);
    }
  }

  // ——————————————————————————————
  // 7. POSITION TRACKING
  // ——————————————————————————————

  /**
   * Update user position from server and animate marker movement
   * @param {boolean} animate - Whether to animate the marker movement
   */
  async function updatePosition(animate = true) {
    try {
      console.log("🔄 Updating position for room:", currentRoom);
      showStatus("Updating position...", "#007AFF");

      // Fetch current position from server
      const response = await fetch(`/position?room=${currentRoom}`);
      if (!response.ok) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      const { position, timestamp, walked_distance } = data;
      
      // Conversion des coordonnées GPS en coordonnées Leaflet
      const [lon, lat] = position;
      const leafletPos = gpsToLeaflet(lon, lat);

      const currentLatLng = userMarker.getLatLng();

      if (animate) {
        animateMarkerMovement(currentLatLng, leafletPos);
      } else {
        userMarker.setLatLng(leafletPos);
      }

      if (!map.getBounds().contains(leafletPos)) {
        map.panTo(leafletPos, { animate: true });
      }

      updateUIElements(lat, lon, timestamp, walked_distance);

    } catch (error) {
      console.error("❌ Position update error:", error);
      showStatus("Position update failed", "#ff4444");
      handleError(error);
    }
  }

  /**
   * Animate marker movement between two positions
   * @param {L.LatLng} startPos - Starting position
   * @param {L.LatLng} endPos - Target position
   */
  function animateMarkerMovement(startPos, endPos) {
    const steps = MAP_CONFIG.ANIMATION_STEPS;
    const deltaLat = (endPos.lat - startPos.lat) / steps;
    const deltaLng = (endPos.lng - startPos.lng) / steps;

    let currentStep = 0;
    
    const animate = () => {
      if (currentStep < steps) {
        currentStep++;
        userMarker.setLatLng([
          startPos.lat + deltaLat * currentStep,
          startPos.lng + deltaLng * currentStep
        ]);
        requestAnimationFrame(animate);
      }
    };
    
    animate();
  }

  /**
   * Update UI elements with new position data
   * @param {number} lat - Latitude
   * @param {number} lng - Longitude  
   * @param {string} timestamp - Position timestamp
   * @param {number} walked_distance - Distance walked
   */
  function updateUIElements(lat, lng, timestamp, walked_distance) {
    const coordsEl = document.getElementById('coordinates');
    const timestampEl = document.getElementById('timestamp');
    const walkedDistanceEl = document.getElementById('walkedDistance');

    if (coordsEl) {
      coordsEl.textContent = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
    }
    
    if (timestampEl) {
      timestampEl.textContent = new Date(timestamp).toLocaleTimeString();
    }
    
    if (walkedDistanceEl && typeof walked_distance === 'number') {
      walkedDistanceEl.textContent = `${walked_distance.toFixed(2)}m`;
    }
  }

  // ——————————————————————————————
  // 8. QR CODE SCANNING
  // ——————————————————————————————

  /**
   * Process QR code scan and update position accordingly
   * @param {string} room - Room identifier from QR code
   */
  async function scanQR(room) {
    try {
      console.log("📱 Processing QR scan for room:", room);
      
      const response = await fetch("/scan_qr", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ room })
      });

      if (!response.ok) {
        throw new Error(`QR scan error: ${response.status}`);
      }
      
      const data = await response.json();
      console.log("✅ QR scan successful:", data);
      showStatus(`QR scanned: Room ${data.room}`, "#4CAF50");

      currentRoom = data.room;
      await updatePosition(false);

      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
      pollingInterval = setInterval(() => updatePosition(true), MAP_CONFIG.UPDATE_INTERVAL);

      collectSensorData();

    } catch (error) {
      console.error("❌ QR scan failed:", error);
      handleError(error);
    }
  }

  window.scanQR = scanQR;

  // ——————————————————————————————
  // 9. ROUTE CALCULATION 
  // ——————————————————————————————

  /**
   * Calculate and display route between two rooms
   * @param {string} fromRoom - Starting room
   * @param {string} toRoom - Destination room
   */
  async function calculateRoute(fromRoom, toRoom) {
    try {
      showStatus("Calculating route...", "#007AFF");

      const response = await fetch(`/route?from=${fromRoom}&to=${toRoom}`);
      if (!response.ok) {
        throw new Error(`Route calculation error: ${response.status}`);
      }

      const geojson = await response.json();
      console.log("📍 Route GeoJSON received:", geojson);

      // Remove existing route if present
      if (routeLayer) {
        map.removeLayer(routeLayer);
      }

      // Convert GeoJSON coordinates from GPS to Leaflet coordinates
      const convertedFeatures = geojson.features.map(feature => {
        const coordinates = feature.geometry.coordinates.map(coord => {
          const [gpsLon, gpsLat] = coord;
          const leafletPos = gpsToLeaflet(gpsLon, gpsLat);
          return [leafletPos.lng, leafletPos.lat];
        });

        return {
          ...feature,
          geometry: {
            ...feature.geometry,
            coordinates: coordinates
          }
        };
      });

      const convertedGeoJSON = {
        ...geojson,
        features: convertedFeatures
      };

      // Add new route with visible styling
      routeLayer = L.geoJSON(convertedGeoJSON, {
        style: {
          color: '#FF0000',
          weight: 6,
          opacity: 1.0,
          dashArray: null
        },
        onEachFeature: function(feature, layer) {
          if (feature.properties && feature.properties.segment_distance) {
            layer.bindTooltip(`${feature.properties.segment_distance.toFixed(1)}m`, 
              {permanent: false, direction: 'center'});
          }
        }
      }).addTo(map);
      
      // Bring to front to ensure visibility
      routeLayer.bringToFront();

      // Center view on route
      const routeBounds = routeLayer.getBounds();
      if (routeBounds.isValid()) {
        map.fitBounds(routeBounds, { padding: [20, 20] });
      }
      
      showStatus(`Route calculated: ${geojson.total_distance?.toFixed(1) || '0.0'}m`, "#4CAF50");
      console.log("✅ Route displayed successfully");

    } catch (error) {
      console.error("❌ Route calculation error:", error);
      showStatus("Route calculation failed", "#ff4444");
      throw error;
    }
  }

  // ——————————————————————————————
  // 10. SENSOR DATA COLLECTION
  // ——————————————————————————————

  /**
   * Collect sensor data from device (accelerometer, gyroscope, magnetometer)
   * Works across different platforms (iOS, Android, Desktop)
   */
  window.collectSensorData = async () => {
    console.log('🔄 Starting multi-platform sensor data collection...');

    // Create status indicator
    const statusDiv = document.createElement('div');
    statusDiv.id = 'sensor-status';
    statusDiv.style.cssText = `
      position: fixed; top: 20px; right: 20px; z-index: 10000;
      background: rgba(0,0,0,0.9); color: white; padding: 12px;
      border-radius: 6px; font-size: 14px; max-width: 300px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    `;
    document.body.appendChild(statusDiv);
    
    const updateStatus = (message, color = 'white') => {
      statusDiv.textContent = `📱 ${message}`;
      statusDiv.style.color = color;
    };

    // Platform detection
    const platformInfo = {
      isIOS: /iPad|iPhone|iPod/.test(navigator.userAgent),
      isAndroid: /Android/.test(navigator.userAgent),
      isMobile: /Mobile|Android|iPhone|iPad/.test(navigator.userAgent),
      userAgent: navigator.userAgent,
      platform: navigator.platform
    };

    console.log('📱 Platform detected:', platformInfo);
    updateStatus(`Platform: ${platformInfo.isIOS ? 'iOS' : platformInfo.isAndroid ? 'Android' : 'Desktop'}`);

    // Check if device motion is available
    if (!window.DeviceMotionEvent) {
      updateStatus('Motion sensors not available', 'orange');
      setTimeout(() => statusDiv.remove(), 3000);
      return;
    }

    /**
     * Collect sensor data from device motion events
     */
    const collectMotionData = () => {
      updateStatus('Collecting sensor data...', '#4CAF50');
      let dataCollected = false;
      
      // Set timeout to prevent hanging
      const collectionTimeout = setTimeout(() => {
        if (!dataCollected) {
          updateStatus('Timeout - sending test data', 'orange');
          sendTestSensorData(platformInfo);
          dataCollected = true;
        }
      }, 3000);

      // Motion event handler
      const handleDeviceMotion = (event) => {
        if (dataCollected) return;
        
        dataCollected = true;
        clearTimeout(collectionTimeout);
        
        // Extract sensor readings
        const sensorData = {
          room: currentRoom,
          timestamp: new Date().toISOString(),
          accelerometer: [{
            x: event.acceleration?.x || 0,
            y: event.acceleration?.y || 0,
            z: event.acceleration?.z || 0
          }],
          gyroscope: [{
            x: event.rotationRate?.alpha || 0,
            y: event.rotationRate?.beta || 0,
            z: event.rotationRate?.gamma || 0
          }],
          magnetometer: [{
            x: event.accelerationIncludingGravity?.x || 0,
            y: event.accelerationIncludingGravity?.y || 0,
            z: event.accelerationIncludingGravity?.z || 0
          }],
          deviceInfo: {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            language: navigator.language,
            screen: `${screen.width}x${screen.height}`,
            devicePixelRatio: window.devicePixelRatio
          }
        };

        updateStatus('Sending sensor data...', '#2196F3');
        sendSensorData(sensorData);
        
        // Clean up event listener
        window.removeEventListener('devicemotion', handleDeviceMotion);
      };

      window.addEventListener('devicemotion', handleDeviceMotion);
    };

    // Handle iOS permission requirements
    if (platformInfo.isIOS && typeof DeviceMotionEvent.requestPermission === 'function') {
      updateStatus('Requesting iOS motion permission...', '#FF9500');
      
      try {
        const permission = await DeviceMotionEvent.requestPermission();
        if (permission === 'granted') {
          collectMotionData();
        } else {
          updateStatus('Motion permission denied', 'red');
          setTimeout(() => statusDiv.remove(), 3000);
        }
      } catch (error) {
        console.error('iOS permission request error:', error);
        updateStatus('Permission request failed', 'red');
        setTimeout(() => statusDiv.remove(), 3000);
      }
    } else {
      // Android and other platforms - no permission required
      collectMotionData();
    }
  };

  /**
   * Send collected sensor data to server
   * @param {Object} data - Sensor data to send
   */
  async function sendSensorData(data) {
    try {
      const response = await fetch('/collect_sensor_data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const result = await response.json();
      console.log('✅ Sensor data sent successfully:', result);

      // Update status indicator
      const statusDiv = document.getElementById('sensor-status');
      if (statusDiv) {
        statusDiv.textContent = '✅ Sensor data sent';
        statusDiv.style.color = '#4CAF50';
        setTimeout(() => statusDiv.remove(), 2000);
      }
      
    } catch (error) {
      console.error('❌ Sensor data transmission error:', error);
      
      const statusDiv = document.getElementById('sensor-status');
      if (statusDiv) {
        statusDiv.textContent = '❌ Transmission failed';
        statusDiv.style.color = 'red';
        setTimeout(() => statusDiv.remove(), 3000);
      }
    }
  }

  /**
   * Send test sensor data when real sensors are unavailable
   * @param {Object} platformInfo - Platform detection information
   */
  function sendTestSensorData(platformInfo) {
    const testData = {
      room: currentRoom,
      timestamp: new Date().toISOString(),
      test: true,
      platform: platformInfo,
      accelerometer: [{ x: 0, y: 0, z: 9.8 }],
      gyroscope: [{ x: 0, y: 0, z: 0 }],
      magnetometer: [{ x: 0, y: 0, z: 0 }]
    };
    
    sendSensorData(testData);
  }

  // ——————————————————————————————
  // 11. BUTTON EVENT HANDLERS
  // ——————————————————————————————

  /**
   * Initialize route calculation button
   */
  function initializeRouteButton() {
    const goBtn = document.getElementById('goBtn');
    if (!goBtn) {
      console.warn("⚠️ Route button 'goBtn' not found");
      return;
    }

    goBtn.addEventListener('click', async () => {
      const destSelect = document.getElementById('destSelect');
      const destination = destSelect?.value;
      
      if (!destination) {
        alert('Please select a destination');
        return;
      }

      try {
        // Disable button during calculation
        goBtn.disabled = true;
        goBtn.textContent = 'Calculating...';

        await calculateRoute(currentRoom, destination);

      } catch (error) {
        alert('Unable to calculate route. Please try again.');
      } finally {
        // Re-enable button
        goBtn.disabled = false;
        goBtn.textContent = 'Route';
      }
    });

    console.log("✅ Route calculation button initialized");
  }

  /**
   * Initialize position recalibration button
   */
  function initializeRecalibrateButton() {
    const recalibrateBtn = document.getElementById('recalibrate');
    if (!recalibrateBtn) {
      console.warn("⚠️ Recalibrate button not found");
      return;
    }

    recalibrateBtn.addEventListener('click', async () => {
      try {
        recalibrateBtn.disabled = true;
        recalibrateBtn.textContent = 'Recalibrating...';
        showStatus("Recalibrating position...", "#FF9500");

        const currentPos = userMarker.getLatLng();
        const response = await fetch('/confirm_position', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            room: currentRoom,
            position: [currentPos.lat, currentPos.lng]
          })
        });

        if (!response.ok) {
          throw new Error(`Recalibration failed: ${response.status}`);
        }

        showStatus("Position recalibrated successfully", "#4CAF50");
        console.log("✅ Position recalibration successful");

      } catch (error) {
        console.error("❌ Recalibration error:", error);
        showStatus("Recalibration failed", "#ff4444");
        handleError(error);
      } finally {
        recalibrateBtn.disabled = false;
        recalibrateBtn.textContent = 'Recalibrate';
      }
    });

    console.log("✅ Position recalibration button initialized");
  }

  // ——————————————————————————————
  // 12. EVENT LISTENERS AND RESPONSIVE HANDLING
  // ——————————————————————————————

  /**
   * Handle window resize events to maintain map layout
   */
  function handleWindowResize() {
    console.log("🖥️ Window resize detected");
    
    setTimeout(() => {
      if (map) {
        map.invalidateSize();
        console.log("✅ Map size recalculated for new window dimensions");
      }
    }, 100);
  }

  /**
   * Handle device orientation changes (mobile)
   */
  function handleOrientationChange() {
    console.log("📱 Device orientation changed");
    
    // Delay to allow orientation change to complete
    setTimeout(() => {
      handleWindowResize();
    }, 300);
  }

  /**
   * Handle page visibility changes to maintain map state
   */
  function handleVisibilityChange() {
    if (!document.hidden && map) {
      // Page became visible - recalculate map size
      setTimeout(() => {
        map.invalidateSize();
        console.log("✅ Map refreshed after page became visible");
      }, 100);
    }
  }

  /**
   * Set up URL monitoring for room changes
   */
  function initializeURLMonitoring() {
    // Listen for browser navigation events
    window.addEventListener('popstate', checkRoomChangeAndUpdatePolling);
    window.addEventListener('hashchange', checkRoomChangeAndUpdatePolling);

    // Fallback: check for URL changes every second
    setInterval(checkRoomChangeAndUpdatePolling, 1000);
    
    console.log("✅ URL monitoring initialized");
  }

  /**
   * Initialize all event listeners
   */
  function initializeEventListeners() {
    window.addEventListener('resize', handleWindowResize);
    window.addEventListener('orientationchange', handleOrientationChange);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    console.log("✅ Event listeners initialized");
  }

  // ——————————————————————————————
  // 13. APPLICATION STARTUP
  // ——————————————————————————————

  /**
   * Start position polling after initialization
   */
  function startPositionPolling() {
    console.log("🔄 Starting position polling...");
    
    // Initial position update
    setTimeout(() => {
      updatePosition(false);
      
      // Start regular polling
      pollingInterval = setInterval(() => {
        updatePosition(true);
      }, MAP_CONFIG.UPDATE_INTERVAL);
      
      console.log(`✅ Position polling started (interval: ${MAP_CONFIG.UPDATE_INTERVAL}ms)`);
    }, 1000);
  }

  /**
   * Main application initialization function
   */
  function initializeApp() {
    try {
      // Step 1: Validate dependencies
      if (!validateDependencies()) {
        return false;
      }

      // Step 2: Initialize room tracking
      initializeRoom();

      // Step 3: Initialize map
      if (!initializeMap()) {
        return false;
      }

      // Step 4: Add user marker
      initializeUserMarker();

      // Step 5: Initialize UI components
      initializeRouteButton();
      initializeRecalibrateButton();

      // Step 6: Set up event listeners
      initializeEventListeners();
      initializeURLMonitoring();

      // Step 7: Start position tracking
      startPositionPolling();

      console.log("✅ === APPLICATION INITIALIZATION COMPLETE ===");
      showStatus("Application ready", "#4CAF50");
      
      return true;

    } catch (error) {
      console.error("❌ Application initialization failed:", error);
      handleError(error);
      return false;
    }
  }

  // ——————————————————————————————
  // 14. START APPLICATION
  // ——————————————————————————————

  initializeApp();
});