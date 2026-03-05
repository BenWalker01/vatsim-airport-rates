use wasm_bindgen::prelude::*;
use wasm_bindgen_futures::JsFuture;
use web_sys::{window, Request, RequestInit, RequestMode};
use crate::models::Pilot;
use crate::state::get_app_state;
use crate::airport::AirportTracker;

/// Fetch real-time VATSIM pilot data from the API
#[wasm_bindgen]
pub async fn fetch_vatsim_data() -> Result<String, JsValue> {
    let window = window().ok_or_else(|| JsValue::from_str("No window object"))?;
    let url = "https://data.vatsim.net/v3/vatsim-data.json";

    let opts = RequestInit::new();
    opts.set_method("GET");
    opts.set_mode(RequestMode::Cors);

    let request = Request::new_with_str_and_init(url, &opts)?;

    let resp_value = JsFuture::from(window.fetch_with_request(&request))
        .await
        .map_err(|_| JsValue::from_str("Fetch failed"))?;

    let resp = web_sys::Response::from(resp_value);
    let text = JsFuture::from(resp.text().map_err(|_| JsValue::from_str("Text failed"))?)
        .await
        .map_err(|_| JsValue::from_str("Text await failed"))?;

    Ok(text.as_string().unwrap_or_default())
}

/// Add an airport to track
#[wasm_bindgen]
pub fn add_airport(icao: &str) -> Result<String, JsValue> {
    let mut state = get_app_state()
        .lock()
        .map_err(|_| JsValue::from_str("Lock failed"))?;

    let icao_upper = icao.to_uppercase();

    if let Some(boundary_data) = state.boundaries.get(&icao_upper) {
        let tracker = AirportTracker::new(
            icao_upper.clone(),
            boundary_data.bounding_box.clone(),
            boundary_data.elevation,
        );
        state.trackers.insert(icao_upper.clone(), tracker);
        Ok(format!("Now tracking {}", icao_upper))
    } else {
        Err(JsValue::from_str("Airport not found in database"))
    }
}

/// Remove an airport from tracking
#[wasm_bindgen]
pub fn remove_airport(icao: &str) -> Result<String, JsValue> {
    let mut state = get_app_state()
        .lock()
        .map_err(|_| JsValue::from_str("Lock failed"))?;

    let icao_upper = icao.to_uppercase();
    if state.trackers.remove(&icao_upper).is_some() {
        Ok(format!("Stopped tracking {}", icao_upper))
    } else {
        Err(JsValue::from_str("Airport not found in active tracking"))
    }
}

/// Process pilot data and calculate airport statistics
#[wasm_bindgen]
pub fn process_pilots_json(
    pilots_json: &str,
    icao: &str,
) -> Result<String, JsValue> {
    let pilots: Vec<Pilot> = serde_json::from_str(pilots_json)
        .map_err(|e| JsValue::from_str(&format!("JSON parse error: {}", e)))?;

    let mut state = get_app_state()
        .lock()
        .map_err(|_| JsValue::from_str("Lock failed"))?;

    let icao_upper = icao.to_uppercase();

    if let Some(tracker) = state.trackers.get_mut(&icao_upper) {
        let stats = tracker.process_pilots(&pilots, js_sys::Date::now() / 1000.0);
        Ok(serde_json::to_string(&stats)
            .map_err(|e| JsValue::from_str(&format!("Serialize error: {}", e)))?)
    } else {
        Err(JsValue::from_str("Airport not being tracked"))
    }
}

/// Get list of available airports to track
#[wasm_bindgen]
pub fn get_available_airports() -> Result<String, JsValue> {
    let state = get_app_state()
        .lock()
        .map_err(|_| JsValue::from_str("Lock failed"))?;

    let airports: Vec<String> = state.boundaries.keys().cloned().collect();
    Ok(serde_json::to_string(&airports)
        .map_err(|e| JsValue::from_str(&format!("Serialize error: {}", e)))?)
}

/// Get list of currently tracked airports
#[wasm_bindgen]
pub fn get_active_airports() -> Result<String, JsValue> {
    let state = get_app_state()
        .lock()
        .map_err(|_| JsValue::from_str("Lock failed"))?;

    let airports: Vec<String> = state.trackers.keys().cloned().collect();
    Ok(serde_json::to_string(&airports)
        .map_err(|e| JsValue::from_str(&format!("Serialize error: {}", e)))?)
}
