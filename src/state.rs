use crate::models::AirportBoundary;
use crate::airport::AirportTracker;
use std::collections::HashMap;
use std::sync::Mutex;

pub struct AppState {
    pub trackers: HashMap<String, AirportTracker>,
    pub boundaries: HashMap<String, AirportBoundary>,
}

pub static APP_STATE: std::sync::OnceLock<Mutex<AppState>> = std::sync::OnceLock::new();

pub fn get_app_state() -> &'static Mutex<AppState> {
    APP_STATE.get_or_init(|| {
        Mutex::new(AppState {
            trackers: HashMap::new(),
            boundaries: load_boundaries(),
        })
    })
}

fn load_boundaries() -> HashMap<String, AirportBoundary> {
    let boundaries_json = include_str!("../static/boundaries.json");
    serde_json::from_str(boundaries_json).unwrap_or_default()
}
