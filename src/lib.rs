mod models;
mod maths;
mod airport;
mod state;
mod api;

use std::panic;
use console_error_panic_hook;
use wasm_bindgen::prelude::*;

#[wasm_bindgen(start)]
pub fn init() {
    panic::set_hook(Box::new(console_error_panic_hook::hook));
}

// Re-export public API functions for convenience
pub use api::{
    fetch_vatsim_data, add_airport, remove_airport, process_pilots_json,
    get_available_airports, get_active_airports,
};

pub use models::{Pilot, FlightPlan, AirportStats, AirportBoundary};
pub use airport::AirportTracker;
