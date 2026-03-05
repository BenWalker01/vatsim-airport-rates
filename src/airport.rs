use crate::models::{Pilot, AirportStats};
use crate::maths::{point_in_polygon, haversine, polygon_center};
use std::collections::HashSet;

const HOUR: f64 = 3600.0;
const ROLLING_RATE: f64 = 15.0 * 60.0;
const APPROACH_RADIUS_KM: f64 = 50.0;

pub struct AirportTracker {
    pub icao: String,
    pub boundary: Vec<[f64; 2]>,
    pub elevation: i32,
    pub center: (f64, f64),
    
    on_ground: HashSet<String>,
    departed: Vec<(String, f64)>,
    dep_hour_track: Vec<(String, f64)>,
    
    on_approach: HashSet<String>,
    arrived: Vec<(String, f64)>,
    arr_hour_track: Vec<(String, f64)>,
}

impl AirportTracker {
    pub fn new(icao: String, boundary: Vec<[f64; 2]>, elevation: i32) -> Self {
        let center = polygon_center(&boundary);
        AirportTracker {
            icao,
            boundary,
            elevation,
            center,
            on_ground: HashSet::new(),
            departed: Vec::new(),
            dep_hour_track: Vec::new(),
            on_approach: HashSet::new(),
            arrived: Vec::new(),
            arr_hour_track: Vec::new(),
        }
    }

    pub fn process_pilots(&mut self, pilots: &[Pilot], current_time: f64) -> AirportStats {
        let mut currently_on_ground = HashSet::new();
        let mut currently_on_approach = HashSet::new();

        // Check each pilot's position
        for pilot in pilots {
            if let Some(plan) = &pilot.flight_plan {
                if plan.flight_rules.as_ref().map_or(false, |r| r == "I") {
                    let point = (pilot.latitude, pilot.longitude);

                    // On ground detection
                    if point_in_polygon(point, &self.boundary)
                        && pilot.altitude < (self.elevation + 200)
                        && plan.departure.as_ref().map_or(false, |d| d == &self.icao)
                    {
                        currently_on_ground.insert(pilot.callsign.clone());
                    }

                    // On approach detection
                    let distance = haversine(
                        self.center.0,
                        self.center.1,
                        pilot.latitude,
                        pilot.longitude,
                    );

                    if distance <= APPROACH_RADIUS_KM
                        && !point_in_polygon(point, &self.boundary)
                        && pilot.altitude > (self.elevation + 200)
                        && plan.arrival.as_ref().map_or(false, |a| a == &self.icao)
                    {
                        currently_on_approach.insert(pilot.callsign.clone());
                    }
                }
            }
        }

        // Track departures
        for callsign in &self.on_ground {
            if !currently_on_ground.contains(callsign) {
                self.departed.push((callsign.clone(), current_time));
                self.dep_hour_track.push((callsign.clone(), current_time));
            }
        }

        // Track arrivals
        for callsign in &self.on_approach {
            if !currently_on_approach.contains(callsign) {
                self.arrived.push((callsign.clone(), current_time));
                self.arr_hour_track.push((callsign.clone(), current_time));
            }
        }

        self.on_ground = currently_on_ground;
        self.on_approach = currently_on_approach;

        // Clean up old entries
        self.departed
            .retain(|(_, time)| current_time - time <= ROLLING_RATE);
        self.dep_hour_track
            .retain(|(_, time)| current_time - time <= HOUR);
        self.arrived
            .retain(|(_, time)| current_time - time <= ROLLING_RATE);
        self.arr_hour_track
            .retain(|(_, time)| current_time - time <= HOUR);

        let rolling_dep_rate = self.departed.len() as f64 * (HOUR / ROLLING_RATE);
        let rolling_arr_rate = self.arrived.len() as f64 * (HOUR / ROLLING_RATE);

        AirportStats {
            icao: self.icao.clone(),
            on_ground: self.on_ground.len(),
            on_approach: self.on_approach.len(),
            rolling_dep_rate,
            rolling_arr_rate,
            actual_dep_rate: self.dep_hour_track.len(),
            actual_arr_rate: self.arr_hour_track.len(),
        }
    }
}
