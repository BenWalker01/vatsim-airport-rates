use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Deserialize)]
pub struct Pilot {
    pub callsign: String,
    pub latitude: f64,
    pub longitude: f64,
    pub altitude: i32,
    pub flight_plan: Option<FlightPlan>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct FlightPlan {
    pub departure: Option<String>,
    pub arrival: Option<String>,
    pub flight_rules: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
pub struct VatsimData {
    pub pilots: Vec<Pilot>,
}

#[derive(Debug, Serialize, Clone)]
pub struct AirportStats {
    pub icao: String,
    pub on_ground: usize,
    pub on_approach: usize,
    pub rolling_dep_rate: f64,
    pub rolling_arr_rate: f64,
    pub actual_dep_rate: usize,
    pub actual_arr_rate: usize,
}

#[derive(Debug, Clone, Deserialize)]
pub struct AirportBoundary {
    #[serde(rename = "boundingBox")]
    pub bounding_box: Vec<[f64; 2]>,
    pub elevation: i32,
}
