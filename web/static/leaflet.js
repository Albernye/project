// Wrap everything to ensure DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
// Mapping from room numbers to PostGIS node IDs
const destinations = {
'201': 50, '202': 48, '203': 46, '204': 42, '205': 38,
'206': 34, '207': 30, '208': 18, '209': 18,
'210': 10, '211': 10, '212': 6, '213': 2,
'214': 4, '215': 8, '216': 12, '217': 16,
'218': 22, '219': 26, '220': 24, '221': 28,
'222': 32, '223': 36, '224': 40, '225': 44,
'exit': 20
 };
// Populate dropdown
const destSelect = document.getElementById('destSelect');
Object.entries(destinations).forEach(([room, node]) => {
if (room === 'exit') return;
const opt = document.createElement('option');
opt.value = node;
opt.textContent = `Room ${room}`;
destSelect.appendChild(opt);
 });
// Bounds of floor plan
const imageBounds = [[41.406776, 2.193289], [41.4065729, 2.1943043]];
// Initialize map
const map = L.map('map', {
crs: L.CRS.EPSG4326,
zoomControl: true,
minZoom: 17,
maxZoom: 22
 });
L.imageOverlay('/static/OBuilding_Floor2.png', imageBounds, {opacity:0.8}).addTo(map);
map.fitBounds(imageBounds);
let routeLayer, userMarker;
// Draw route
async function drawRoute(fromNode, toNode) {
try {
const resp = await fetch(`/route?from=${fromNode}&to=${toNode}`);
const json = await resp.json();
console.log('Route response:', json);
if (json.status !== 'success') {
alert('Error drawing route: ' + json.message);
return;
 }
const fc = json.route;
console.log('Full route data structure:', JSON.stringify(fc, null, 2));
if (!fc.features || fc.features.length === 0) {
alert('No route found');
return;
 }
console.log('First feature:', fc.features[0]);
console.log('Geometry:', fc.features[0].geometry);
if (routeLayer) map.removeLayer(routeLayer);
routeLayer = L.geoJSON(fc, { style: { color: 'blue', weight: 4 } }).addTo(map);
// Derive initial marker position from raw GeoJSON coords
let rawCoords = fc.features[0].geometry.coordinates;
console.log('Raw coordinates:', rawCoords);
// Vérifier si rawCoords existe et n'est pas vide
if (!rawCoords || rawCoords.length === 0) {
console.error('No coordinates found in route data');
alert('No coordinates found in route');
return;
 }
// Flatten one level if nested arrays
if (Array.isArray(rawCoords[0]) && Array.isArray(rawCoords[0][0])) {
rawCoords = rawCoords.flat();
 }
// Vérifier à nouveau après le flat()
if (!rawCoords || rawCoords.length === 0) {
console.error('No coordinates after flattening');
alert('Invalid coordinate data');
return;
 }
console.log('Processed coordinates:', rawCoords);
// Vérifier que le premier élément existe et a au moins 2 coordonnées
if (!rawCoords[0] || rawCoords[0].length < 2) {
console.error('Invalid first coordinate:', rawCoords[0]);
alert('Invalid coordinate format');
return;
 }
const [initLon, initLat] = rawCoords[0];
console.log('Initial position:', initLat, initLon);
if (!userMarker) {
userMarker = L.marker([initLat, initLon]).addTo(map);
 } else {
userMarker.setLatLng([initLat, initLon]);
 }
 } catch (e) {
console.error('Error in drawRoute:', e);
alert('Failed to draw route');
 }
 }
// Go button
document.getElementById('goBtn').addEventListener('click', () => {
const destNode = destSelect.value;
const params = new URLSearchParams(window.location.search);
const room = params.get('room');
const currentNode = destinations[room];
if (!currentNode) {
alert('Current unknown');
return;
 }
drawRoute(currentNode, destNode);
 });
// Optional simulate movement
let idx = 0;
setInterval(() => {
if (!routeLayer || !userMarker) return;
const layers = routeLayer.getLayers();
if (layers.length === 0) return;
const coords = layers[0].getLatLngs();
if (coords.length === 0) return;
idx = (idx + 1) % coords.length;
userMarker.setLatLng(coords[idx]);
 }, 1000);
});