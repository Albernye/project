
# 🤖 GitHub Copilot Instruction Prompt for Indoor Routing & Localization System

## Project Context
* **Architecture**:
	- `algorithms/` (PDR, Wi‑Fi fingerprinting [deprecated], fusion filters)
	- `web/` (Flask `app.py`, JS in `static/` for sensors and QR scanning)
	- `scripts/` (CLI tools: `record_realtime.py`, `init_stats.py`, `geolocate.py`, `send_email.py`)
	- `data/` (CSV logs, `room_positions.csv`, `corridor_graph.json`)
	- `qr_generator/` (QR code creation)
	- `tests/` (shell/API tests, Python unit tests)

* **Current Focus**:
	1. **Remove Wi‑Fi fingerprinting** from fusion pipeline
		 - Code is commented but function signatures still accept Wi‑Fi input
		 - Fusion should now only merge PDR and QR recalibration
	2. **Fix email alerts** when a QR code is scanned
		 - Ensure `scripts/send_email.py` is invoked correctly from web handler
		 - Add unit tests + integration tests
	3. **Front‑end improvements** (coming next)

## Tasks for Copilot
1. **Refactor Fusion Logic**
	 - In `algorithms/fusion.py`:
		 - Remove deprecated Wi‑Fi arguments from function signatures
		 - Update fusion algorithm to blend only PDR and QR updates (Kalman filter)
		 - Clean up commented Wi‑Fi code (keep for reference)
	 - Add unit tests in `tests/test_fusion.py` covering:
		 - PDR‑only prediction + QR correction
		 - Edge cases (no QR in range, frequent QR hits)

2. **Email Notification on QR Scan**
	 - In `web/app.py` (QR scan route):
		 - Import and call `scripts/send_email.send_alert(recipient, room_id)`
		 - Handle errors and log success/failure
	 - In `scripts/send_email.py`:
		 - Verify SMTP settings, error handling, test stub
		 - Add unit tests in `tests/test_send_email.py`
	 - Add integration test in `tests/api_test_qr_email.sh` to verify HTTP route triggers email stub

3. **Route `/position` Repair**
   - In `web/app.py`:
     - Inspect `/position` handler: identify where a `Path` is returned or iterated
     - Convert `PosixPath` or file paths to list/dict before JSONify
     - Add unit tests in `tests/test_position.py` covering:
       - Valid room query returns list of coordinate tuples
       - No PDR data returns default position
4. **Testing & Validation**
	 - Ensure all new tests pass via `bash tests/run_all.sh`
	 - Validate server launch: `python web/app.py` returns HTTP 200 for fusion and QR endpoints

5. **Next Steps (Frontend)**
	 - Scaffold placeholder TODO comments in `web/static/js/main.js` for:
		 - UI feedback on email send
		 - Error modals
		 - Sensor data overlay

## Developer Conventions
- Keep deprecated code commented, don’t delete
- Use existing shell test scripts patterns
- Match naming: functions, file headers, `TODO: COPILOT`

---
*Place this block at the top of your VSCode editor to guide Copilot’s completions.*
