const EARTH_RADIUS_KM: f64 = 6372.8;

/// Haversine formula to calculate distance between two points on Earth
pub fn haversine(lat1: f64, lon1: f64, lat2: f64, lon2: f64) -> f64 {
    let dlat = (lat2 - lat1).to_radians();
    let dlon = (lon2 - lon1).to_radians();
    let lat1_rad = lat1.to_radians();
    let lat2_rad = lat2.to_radians();

    let a = (dlat / 2.0).sin().powi(2)
        + lat1_rad.cos() * lat2_rad.cos() * (dlon / 2.0).sin().powi(2);
    let c = 2.0 * a.sqrt().asin();

    EARTH_RADIUS_KM * c
}

/// Ray casting algorithm for point-in-polygon test
pub fn point_in_polygon(point: (f64, f64), polygon: &[[f64; 2]]) -> bool {
    let (x, y) = point;
    let mut inside = false;
    let n = polygon.len();

    let mut p1 = polygon[0];
    for i in 1..=n {
        let p2 = polygon[i % n];
        if y > p1[1].min(p2[1]) {
            if y <= p1[1].max(p2[1]) {
                if x <= p1[0].max(p2[0]) {
                    if p1[1] != p2[1] {
                        let xinters = (y - p1[1]) * (p2[0] - p1[0]) / (p2[1] - p1[1]) + p1[0];
                        if p1[0] == p2[0] || x <= xinters {
                            inside = !inside;
                        }
                    }
                }
            }
        }
        p1 = p2;
    }
    inside
}

/// Calculate the center point of a polygon
pub fn polygon_center(polygon: &[[f64; 2]]) -> (f64, f64) {
    let sum_lat: f64 = polygon.iter().map(|p| p[0]).sum();
    let sum_lon: f64 = polygon.iter().map(|p| p[1]).sum();
    (sum_lat / polygon.len() as f64, sum_lon / polygon.len() as f64)
}
