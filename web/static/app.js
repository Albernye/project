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
  // 2. ROOM DETECTION AND URL MANAGEMENT
  // ——————————————————————————————

  /**
   * Get the current room from URL parameters or map element data
   * @returns {string} Room identifier
   */
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

      // Écriture d'un événement QR côté serveur
      fetch('/change_room', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room: newRoom })
      })
      .then(res => res.json())
      .then(data => {
        console.log('✅ QR event written for room:', data.room);
        // Clear existing polling interval
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
  // 3. DIAGNOSTIC AND VALIDATION
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
  // 4. MAP INITIALIZATION
  // ——————————————————————————————

  /**
   * Initialize Leaflet map with custom coordinate system
   * @returns {boolean} True if initialization successful
   */
  function initializeMap() {
    try {
      console.log("Creating Leaflet map instance...");

      // Create map with Simple CRS for pixel-based coordinates
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
    
    // Default position (will be updated by position polling)
    userMarker = L.marker([41.406368, 2.175568], {
      title: 'Your current position',
      draggable: false
    }).addTo(map);
    
    console.log("✅ User marker added to map");
  }

  // ——————————————————————————————
  // 5. UTILITY FUNCTIONS
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
  // 6. POSITION TRACKING
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
      const [lng, lat] = position;

      const currentLatLng = userMarker.getLatLng();
      const newLatLng = L.latLng(lat, lng);

      // Smooth animation if requested
      if (animate) {
        animateMarkerMovement(currentLatLng, newLatLng);
      } else {
        userMarker.setLatLng(newLatLng);
      }

      // Pan to marker only if it's outside the current view
      if (!map.getBounds().contains(newLatLng)) {
        map.panTo(newLatLng, { animate: true });
      }

      // Update UI elements with new data
      updateUIElements(lat, lng, timestamp, walked_distance);

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
  // 7. QR CODE SCANNING
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

      // Update current room and position
      currentRoom = data.room;
      await updatePosition(false); // Immediate update without animation

      // Restart polling with new room context
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
      pollingInterval = setInterval(() => updatePosition(true), MAP_CONFIG.UPDATE_INTERVAL);

      // Automatically start sensor data collection
      collectSensorData();

    } catch (error) {
      console.error("❌ QR scan failed:", error);
      handleError(error);
    }
  }

  // Make scanQR available globally for QR code integration
  window.scanQR = scanQR;

  // ——————————————————————————————
  // 8. ROUTE CALCULATION
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

      // Add new route with visible styling
      routeLayer = L.geoJSON(geojson, {
        style: {
          color: '#FF0000',     // Red for high visibility
          weight: 6,            // Thick line
          opacity: 1.0,         // Full opacity
          dashArray: null       // Solid line
        }
      }).addTo(map);

      // Ensure route appears above floor plan
      routeLayer.bringToFront();

      // Center view on route without changing zoom
      const routeCenter = routeLayer.getBounds().getCenter();
      map.setView(routeCenter, map.getZoom());
      
      showStatus(`Route calculated: ${geojson.total_distance?.toFixed(1)}m`, "#4CAF50");
      console.log("✅ Route displayed successfully");

    } catch (error) {
      console.error("❌ Route calculation error:", error);
      showStatus("Route calculation failed", "#ff4444");
      throw error;
    }
  }

  // ——————————————————————————————
  // 9. SENSOR DATA COLLECTION
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
  // 10. BUTTON EVENT HANDLERS
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
        goBtn.textContent = 'Calculate Route';
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
        recalibrateBtn.textContent = 'Recalibrate Position';
      }
    });

    console.log("✅ Position recalibration button initialized");
  }

  // ——————————————————————————————
  // 11. EVENT LISTENERS AND RESPONSIVE HANDLING
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
  // 12. APPLICATION STARTUP
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
  // 13. START APPLICATION
  // ——————————————————————————————

  // Initialize the application
  initializeApp();
});