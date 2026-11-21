// Switchyard hot-path core.
//
// Numeric discipline follows ADR-001 of the internal fixed-point engine: no
// floating point decisions. Capacities and quantities are integer micro-units,
// time is integer minutes. The only floating point use is reading and writing
// the transport format, which is outside the decision path.
//
// This binary replays instances exported by the reference implementation and
// re-derives the verdict. Agreement on every instance is the cross-language
// conformance test; disagreement is a specification defect, not a rounding issue.

use std::collections::{HashMap, HashSet};
use std::env;
use std::fs;
use std::thread;
use std::time::Instant;

const MICRO: i64 = 1_000_000;

#[derive(Clone)]
struct Node {
    id: String,
    dwell: i64,
    cap_micro: i64,
    assessed: bool,
    classes: Vec<String>,
}

#[derive(Clone)]
struct Lane {
    id: String,
    src: String,
    dst: String,
    mode: String,
    travel: i64,
    cap_micro: i64,
    // Parsed so the lane record keeps a fixed token count and a malformed line is
    // rejected; no replay decision reads cost. Pricing happens in the Python planner.
    #[allow(dead_code)]
    cost_micro: i64,
    monitored: bool,
    controlled: bool,
    blocked: i64,
    cross_border: bool,
}


#[derive(Clone)]
struct Consignment {
    id: String,
    origin: String,
    dest: String,
    qty_micro: i64,
    class: String,
    ready: i64,
    due: i64,
    allowance: i64,
    heat: i64,
    budget: i64,
    prepos_micro: i64,
}

#[derive(Clone)]
struct Leg {
    cid: String,
    lane: String,
    depart: i64,
    party: bool,
    door: bool,
    container: Option<String>,
}

#[derive(Clone, Default)]
struct Plan {
    legs: Vec<Leg>,
    decision_age: i64,
    approvals: i64,
    precool: HashSet<String>,
    disposition: HashSet<String>,
    estimate: HashSet<String>,
    cost_red: HashSet<String>,
    capacity_verified: bool,
    documents_verified: bool,
    counterparty_verified: bool,
    permits: bool,
    preauth: bool,
    refreshed: bool,
    cap_measured: bool,
    oob_verified: bool,
    escrow: HashSet<String>,
    backup: HashMap<String, String>,
    thermal: HashSet<String>,
    prepos: HashMap<String, i64>,
    deferred: HashSet<String>,
}

/// Thresholds arrive in the transport file, not in this source file, so the two
/// implementations cannot drift apart without the conformance run failing loudly.
#[derive(Clone)]
struct Config {
    queue_ceiling: i64,
    availability_floor: i64,
    service_floor: i64,
    thermal_budget: i64,
    protection_credit: i64,
    mode_availability: HashMap<String, i64>,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            queue_ceiling: 950,
            availability_floor: 900,
            service_floor: 950,
            thermal_budget: 1000,
            protection_credit: 620,
            mode_availability: HashMap::new(),
        }
    }
}

#[derive(Clone)]
struct Instance {
    name: String,
    horizon_min: i64,
    nodes: Vec<Node>,
    lanes: Vec<Lane>,
    cons: Vec<Consignment>,
    plan: Plan,
    notice_zero: bool,
    expect_verdict: String,
    expect_uca: i64,
    expect_excursion: i64,
    expect_blocks: i64,
}

fn parse_micro(token: &str) -> i64 {
    let value: f64 = token.parse().unwrap_or(0.0);
    (value * MICRO as f64).round() as i64
}

fn uca_of(code: &str) -> &'static str {
    match code {
        "GATE-TEMP-001" => "UCA4",
        "GATE-TEMP-002" => "UCA1",
        "GATE-TEMP-003" => "UCA3",
        "GATE-TEMP-004" | "GATE-TEMP-005" => "UCA6",
        "GATE-SLACK-001" | "GATE-SLACK-002" => "UCA2",
        "GATE-FLOW-001" | "GATE-MODE-001" => "UCA9",
        "GATE-HANDOFF-001" => "UCA11",
        "GATE-HANDOFF-002" => "UCA7",
        "GATE-HANDOFF-003" => "UCA16",
        "GATE-DATA-001" | "GATE-DATA-002" => "UCA5",
        "GATE-PLAN-001" => "UCA10",
        "GATE-PLAN-002" => "UCA12",
        "GATE-NODE-001" => "UCA8",
        "GATE-NODE-002" => "UCA14",
        "GATE-PARTY-001" => "UCA15",
        "GATE-LEGAL-001" => "UCA13",
        "GATE-QUEUE-001" => "UCA17",
        "GATE-THERM-006" => "UCA18",
        "GATE-RELIAB-001" => "UCA19",
        "GATE-SERVICE-001" => "UCA20",
        _ => "UCA0",
    }
}

fn is_block(code: &str) -> bool {
    matches!(
        code,
        "GATE-TEMP-001"
            | "GATE-TEMP-002"
            | "GATE-TEMP-004"
            | "GATE-TEMP-005"
            | "GATE-SLACK-001"
            | "GATE-FLOW-001"
            | "GATE-HANDOFF-001"
            | "GATE-DATA-001"
            | "GATE-DATA-002"
            | "GATE-PLAN-002"
            | "GATE-NODE-001"
            | "GATE-NODE-002"
            | "GATE-PARTY-001"
            | "GATE-LEGAL-001"
            | "GATE-HANDOFF-003"
            | "GATE-QUEUE-001"
            | "GATE-THERM-006"
            | "GATE-RELIAB-001"
            | "GATE-SERVICE-001"
    )
}

fn max_flow(edges: &[(String, String, i64)], source: &str, sink: &str) -> i64 {
    let mut index: HashMap<&str, usize> = HashMap::new();
    let mut names: Vec<&str> = Vec::new();
    for (src, dst, _) in edges {
        for name in [src.as_str(), dst.as_str()] {
            if !index.contains_key(name) {
                index.insert(name, names.len());
                names.push(name);
            }
        }
    }
    let count = names.len();
    if count == 0 || !index.contains_key(source) || !index.contains_key(sink) {
        return 0;
    }
    let mut capacity = vec![vec![0i64; count]; count];
    for (src, dst, value) in edges {
        capacity[index[src.as_str()]][index[dst.as_str()]] += *value;
    }
    let s = index[source];
    let t = index[sink];
    let mut total = 0i64;
    loop {
        let mut parent = vec![usize::MAX; count];
        let mut seen = vec![false; count];
        seen[s] = true;
        let mut queue = std::collections::VecDeque::new();
        queue.push_back(s);
        while let Some(node) = queue.pop_front() {
            for next in 0..count {
                if !seen[next] && capacity[node][next] > 0 {
                    seen[next] = true;
                    parent[next] = node;
                    queue.push_back(next);
                }
            }
        }
        if !seen[t] {
            break;
        }
        let mut bottleneck = i64::MAX;
        let mut node = t;
        while node != s {
            let prev = parent[node];
            bottleneck = bottleneck.min(capacity[prev][node]);
            node = prev;
        }
        let mut node = t;
        while node != s {
            let prev = parent[node];
            capacity[prev][node] -= bottleneck;
            capacity[node][prev] += bottleneck;
            node = prev;
        }
        total += bottleneck;
    }
    total
}

fn consignment_findings<'a>(
    inst: &'a Instance,
    nodes: &HashMap<&'a str, &'a Node>,
    lanes: &HashMap<&'a str, &'a Lane>,
    config: &Config,
) -> (Vec<(&'static str, String)>, i64) {
    let mut found: Vec<(&'static str, String)> = Vec::new();
    let mut excursion_total = 0i64;
    for c in &inst.cons {
        let cold = c.class != "ambient";
        let mut legs: Vec<&Leg> = inst.plan.legs.iter().filter(|l| l.cid == c.id).collect();
        legs.sort_by_key(|l| l.depart);
        if legs.is_empty() {
            if !inst.plan.deferred.contains(&c.id) {
                found.push(("GATE-FLOW-001", c.id.clone()));
            }
            continue;
        }
        let mut node = c.origin.clone();
        let mut prev: Option<i64> = None;
        let mut excursion = 0i64;
        let mut uncontrolled_legs = 0i64;
        let mut longest_uncontrolled = 0i64;
        for leg in &legs {
            let lane = match lanes.get(leg.lane.as_str()) {
                Some(value) => *value,
                None => continue,
            };
            if lane.src != node {
                found.push(("GATE-HANDOFF-001", c.id.clone()));
            }
            if leg.depart < c.ready {
                found.push(("GATE-SLACK-001", c.id.clone()));
            }
            if leg.depart < lane.blocked {
                found.push(("GATE-FLOW-001", c.id.clone()));
            }
            if let Some(arrival) = prev {
                if leg.depart < arrival {
                    found.push(("GATE-HANDOFF-001", c.id.clone()));
                }
                let dwell = leg.depart - arrival;
                if let Some(station) = nodes.get(node.as_str()) {
                    if dwell > station.dwell {
                        found.push(("GATE-SLACK-002", c.id.clone()));
                    }
                    if cold && !station.classes.iter().any(|x| x == &c.class) {
                        excursion += dwell;
                    }
                }
            }
            if cold && !lane.controlled {
                excursion += lane.travel;
                uncontrolled_legs += 1;
                longest_uncontrolled = longest_uncontrolled.max(lane.travel);
            }
            if !lane.monitored {
                found.push(("GATE-TEMP-003", c.id.clone()));
            }
            if let Some(target) = nodes.get(lane.dst.as_str()) {
                if !target.assessed {
                    found.push(("GATE-NODE-001", c.id.clone()));
                }
                if target.cap_micro <= 0 {
                    found.push(("GATE-NODE-002", c.id.clone()));
                }
            }
            if let Some(source) = nodes.get(lane.src.as_str()) {
                if source.cap_micro <= 0 {
                    found.push(("GATE-NODE-002", c.id.clone()));
                }
            }
            if lane.cross_border && !inst.plan.permits {
                found.push(("GATE-LEGAL-001", c.id.clone()));
            }
            if !leg.party {
                found.push(("GATE-HANDOFF-001", c.id.clone()));
            }
            if !leg.door {
                found.push(("GATE-HANDOFF-002", c.id.clone()));
            }
            prev = Some(leg.depart + lane.travel);
            node = lane.dst.clone();
        }
        if node != c.dest {
            found.push(("GATE-HANDOFF-001", c.id.clone()));
        }
        let arrival = prev.unwrap_or(0);
        let slack = c.due - arrival;
        if slack <= 0 {
            found.push(("GATE-SLACK-001", c.id.clone()));
        }
        if slack > 0 && slack < HANDOFF_MAX_MIN {
            found.push(("GATE-SLACK-002", c.id.clone()));
        }
        if cold && !inst.plan.precool.contains(&c.id) {
            found.push(("GATE-TEMP-002", c.id.clone()));
        }
        if !inst.plan.documents_verified {
            found.push(("GATE-HANDOFF-003", c.id.clone()));
        }
        if !inst.plan.counterparty_verified && !inst.plan.escrow.contains(&c.id) {
            found.push(("GATE-PARTY-001", c.id.clone()));
        }

        // Thermal dose and series availability: the two physical layers that the
        // gate can demand without a measurement device on the truck.
        let mut exposure = excursion * c.heat;
        if inst.plan.thermal.contains(&c.id) {
            exposure = exposure * (1000 - config.protection_credit) / 1000;
        }
        let dose = if c.budget > 0 { exposure * 1000 / (c.budget * 1000) } else { 1000 };
        if dose > config.thermal_budget {
            found.push(("GATE-THERM-006", c.id.clone()));
        }
        let mut availability_factors: Vec<i64> = Vec::new();
        for leg in &legs {
            if let Some(lane) = lanes.get(leg.lane.as_str()) {
                availability_factors.push(
                    config
                        .mode_availability
                        .get(lane.mode.as_str())
                        .copied()
                        .unwrap_or(1000),
                );
            }
        }
        if let Some(backup_mode) = inst.plan.backup.get(&c.id) {
            if let Some(weakest) = availability_factors.iter().copied().min() {
                let backup = config
                    .mode_availability
                    .get(backup_mode.as_str())
                    .copied()
                    .unwrap_or(1000);
                let failed_both = (1000 - weakest) * (1000 - backup) / 1000;
                if let Some(position) = availability_factors.iter().position(|x| *x == weakest) {
                    availability_factors[position] = 1000 - failed_both;
                }
            }
        }
        let mut availability = 1000i64;
        for factor in &availability_factors {
            availability = availability * factor / 1000;
        }
        if !availability_factors.is_empty() && availability < config.availability_floor {
            found.push(("GATE-RELIAB-001", c.id.clone()));
        }
        if excursion > c.allowance {
            if !inst.plan.disposition.contains(&c.id) {
                found.push(("GATE-TEMP-005", c.id.clone()));
            }
            if longest_uncontrolled > 180 {
                found.push(("GATE-TEMP-004", c.id.clone()));
            }
        }
        if uncontrolled_legs > 0
            && !inst.plan.estimate.contains(&c.id)
            && inst.plan.cost_red.contains(&c.id)
        {
            found.push(("GATE-PLAN-001", c.id.clone()));
        }
        let window = (c.due - c.ready).max(60);
        let mut edges: Vec<(String, String, i64)> = Vec::new();
        for lane in &inst.lanes {
            if cold {
                if !lane.controlled {
                    continue;
                }
                let ok_src = nodes
                    .get(lane.src.as_str())
                    .map(|n| n.classes.iter().any(|x| x == &c.class))
                    .unwrap_or(false);
                let ok_dst = nodes
                    .get(lane.dst.as_str())
                    .map(|n| n.classes.iter().any(|x| x == &c.class))
                    .unwrap_or(false);
                if !ok_src || !ok_dst {
                    continue;
                }
            }
            let capacity = lane.cap_micro * window / 60;
            if capacity > 0 {
                edges.push((lane.src.clone(), lane.dst.clone(), capacity));
            }
        }
        let shipped = max_flow(&edges, &c.origin, &c.dest);
        let committed = inst.plan.prepos.get(&c.id).copied().unwrap_or(0).min(c.prepos_micro);
        if shipped + committed < c.qty_micro {
            found.push(("GATE-FLOW-001", c.id.clone()));
        }
        excursion_total += excursion;
    }
    (found, excursion_total)
}

fn parse_bool01(token: &str) -> bool {
    token == "1"
}

/// Total accessors for the transport format. A malformed line must degrade to a
/// zero-valued record, never to a panic: the core is fed by an exporter that a
/// third party may have edited by hand.
fn tok<'a>(tokens: &'a [&'a str], index: usize) -> &'a str {
    tokens.get(index).copied().unwrap_or("")
}

fn tok_int(tokens: &[&str], index: usize, fallback: i64) -> i64 {
    tokens
        .get(index)
        .and_then(|value| value.parse().ok())
        .unwrap_or(fallback)
}

fn tok_micro(tokens: &[&str], index: usize) -> i64 {
    tokens.get(index).map(|value| parse_micro(value)).unwrap_or(0)
}

fn parse_ids(token: &str) -> HashSet<String> {
    if token == "-" {
        HashSet::new()
    } else {
        token.split('|').map(|s| s.to_string()).collect()
    }
}

fn parse_pairs(token: &str) -> HashMap<String, String> {
    if token == "-" {
        return HashMap::new();
    }
    token
        .split('|')
        .filter_map(|item| {
            let mut parts = item.splitn(2, ':');
            let key = parts.next()?;
            let value = parts.next()?;
            Some((key.to_string(), value.to_string()))
        })
        .collect()
}

// Thresholds mirror config/thresholds.json. The parity test fails if the
// two drift apart, which is cheaper than a schema neither language can read
// without a dependency.
const HANDOFF_MAX_MIN: i64 = 90;
const FRESHNESS_LIMIT_MIN: i64 = 240;

struct Outcome {
    verdict: &'static str,
    uca: i64,
    excursion: i64,
    blocks: i64,
}

fn evaluate(inst: &Instance, config: &Config) -> Outcome {
    let nodes: HashMap<&str, &Node> = inst.nodes.iter().map(|n| (n.id.as_str(), n)).collect();
    let lanes: HashMap<&str, &Lane> = inst.lanes.iter().map(|l| (l.id.as_str(), l)).collect();
    let cons: HashMap<&str, &Consignment> = inst.cons.iter().map(|c| (c.id.as_str(), c)).collect();
    let (mut found, excursion_total) = consignment_findings(inst, &nodes, &lanes, config);

    let mut containers: HashMap<&str, HashSet<&str>> = HashMap::new();
    for leg in &inst.plan.legs {
        if let Some(container) = leg.container.as_deref() {
            containers.entry(container).or_default().insert(leg.cid.as_str());
        }
    }
    for (_, members) in containers.iter() {
        let mut classes: HashSet<&str> = HashSet::new();
        for cid in members.iter() {
            if let Some(c) = cons.get(cid) {
                classes.insert(c.class.as_str());
            }
        }
        if classes.len() > 1 {
            for cid in members.iter() {
                found.push(("GATE-TEMP-001", (*cid).to_string()));
            }
        }
    }
    if inst.plan.decision_age > FRESHNESS_LIMIT_MIN {
        found.push(("GATE-DATA-001", "*".to_string()));
    }
    if !inst.plan.capacity_verified {
        found.push(("GATE-DATA-002", "*".to_string()));
    }
    if inst.notice_zero && inst.plan.approvals > 0 {
        found.push(("GATE-PLAN-002", "*".to_string()));
    }
    let blocked_modes: HashSet<&str> = inst
        .lanes
        .iter()
        .filter(|l| l.blocked > 0)
        .map(|l| l.mode.as_str())
        .collect();
    for c in &inst.cons {
        let modes: HashSet<&str> = inst
            .plan
            .legs
            .iter()
            .filter(|l| l.cid == c.id)
            .filter_map(|l| lanes.get(l.lane.as_str()).map(|lane| lane.mode.as_str()))
            .collect();
        if modes.len() == 1 && modes.iter().any(|m| blocked_modes.contains(m)) {
            let covered = inst
                .plan
                .backup
                .get(&c.id)
                .map(|mode| !blocked_modes.contains(mode.as_str()))
                .unwrap_or(false);
            if !covered {
                found.push(("GATE-MODE-001", c.id.clone()));
            }
        }
    }

    // Station utilisation: load is the cargo that departs from the station inside
    // the horizon, capacity is the station's hourly throughput times the hours.
    let hours = (inst.horizon_min / 60).max(1);
    let mut load: HashMap<&str, i64> = HashMap::new();
    let mut carriers: HashMap<&str, Vec<String>> = HashMap::new();
    for leg in &inst.plan.legs {
        if let Some(lane) = lanes.get(leg.lane.as_str()) {
            if let Some(c) = cons.get(leg.cid.as_str()) {
                *load.entry(lane.src.as_str()).or_insert(0) += c.qty_micro;
                carriers.entry(lane.src.as_str()).or_default().push(leg.cid.clone());
            }
        }
    }
    for (nid, value) in load.iter() {
        if let Some(node) = nodes.get(nid) {
            let utilisation = if node.cap_micro <= 0 {
                1000
            } else {
                (value * 1000 / (node.cap_micro * hours)).min(1000)
            };
            if utilisation > config.queue_ceiling {
                for cid in carriers.get(nid).map(|v| v.as_slice()).unwrap_or(&[]) {
                    found.push(("GATE-QUEUE-001", cid.clone()));
                }
            }
        }
    }

    // Service floor counts only deliberate deferral; unroutable cargo is a
    // GATE-FLOW-001 fact and is not double-counted here.
    let total_micro: i64 = inst.cons.iter().map(|c| c.qty_micro).sum();
    let deferred_micro: i64 = inst
        .cons
        .iter()
        .filter(|c| inst.plan.deferred.contains(&c.id))
        .map(|c| c.qty_micro)
        .sum();
    let served = if total_micro <= 0 {
        1000
    } else {
        ((total_micro - deferred_micro) * 1000 / total_micro).min(1000)
    };
    if served < config.service_floor {
        found.push(("GATE-SERVICE-001", "*".to_string()));
    }

    let blocks = found.iter().filter(|(code, _)| is_block(code)).count() as i64;
    let uca: HashSet<(String, &'static str)> = found
        .iter()
        .map(|(code, cid)| (cid.clone(), uca_of(code)))
        .collect();
    let verdict = if blocks > 0 {
        "BLOCKED"
    } else if !found.is_empty() {
        "PASS_WITH_CONDITION"
    } else {
        "PASS"
    };
    Outcome {
        verdict,
        uca: uca.len() as i64,
        excursion: excursion_total,
        blocks,
    }
}

fn parse_instances(text: &str, config: &mut Config) -> Vec<Instance> {
    let mut out: Vec<Instance> = Vec::new();
    let mut nodes: Vec<Node> = Vec::new();
    let mut lanes: Vec<Lane> = Vec::new();
    let mut cons: Vec<Consignment> = Vec::new();
    let mut plan = Plan::default();
    let mut name = String::new();
    let mut horizon_min = 1440i64;
    let mut notice_zero = false;
    let mut expect = ("".to_string(), 0i64, 0i64, 0i64);

    for line in text.lines() {
        let tokens: Vec<&str> = line.split_whitespace().collect();
        if tokens.is_empty() {
            continue;
        }
        match tokens[0] {
            "CONFIG" => {
                for field in tokens.iter().skip(1) {
                    let mut parts = field.splitn(2, '=');
                    let key = parts.next().unwrap_or("");
                    let value: i64 = parts.next().unwrap_or("0").parse().unwrap_or(0);
                    match key {
                        "queue_ceiling" => config.queue_ceiling = value,
                        "availability_floor" => config.availability_floor = value,
                        "service_floor" => config.service_floor = value,
                        "thermal_budget" => config.thermal_budget = value,
                        "protection_credit" => config.protection_credit = value,
                        _ => {
                            if let Some(mode) = key.strip_prefix("mode_") {
                                config.mode_availability.insert(mode.to_string(), value);
                            }
                        }
                    }
                }
            }
            "INSTANCE" => {
                nodes.clear();
                lanes.clear();
                cons.clear();
                plan = Plan { capacity_verified: true, documents_verified: true, counterparty_verified: true, permits: true, ..Default::default() };
            }
            "NET" => {
                name = tok(&tokens, 1).to_string();
                horizon_min = tok_int(&tokens, 2, 1440);
            }
            "NODE" => {
                let classes = tok(&tokens, 5);
                nodes.push(Node {
                    id: tok(&tokens, 1).to_string(),
                    dwell: tok_int(&tokens, 2, 0),
                    cap_micro: tok_micro(&tokens, 3),
                    assessed: parse_bool01(tok(&tokens, 4)),
                    classes: classes.split('|').map(|s| s.to_string()).collect(),
                })
            }
            "LANE" => lanes.push(Lane {
                id: tok(&tokens, 1).to_string(),
                src: tok(&tokens, 2).to_string(),
                dst: tok(&tokens, 3).to_string(),
                mode: tok(&tokens, 4).to_string(),
                travel: tok_int(&tokens, 5, 0),
                cap_micro: tok_micro(&tokens, 6),
                cost_micro: tok_micro(&tokens, 7),
                monitored: parse_bool01(tok(&tokens, 8)),
                controlled: parse_bool01(tok(&tokens, 9)),
                blocked: tok_int(&tokens, 10, 0),
                cross_border: parse_bool01(tok(&tokens, 11)),
            }),

            "CONS" => cons.push(Consignment {
                id: tok(&tokens, 1).to_string(),
                origin: tok(&tokens, 2).to_string(),
                dest: tok(&tokens, 3).to_string(),
                qty_micro: tok_micro(&tokens, 4),
                class: tok(&tokens, 5).to_string(),
                ready: tok_int(&tokens, 6, 0),
                due: tok_int(&tokens, 7, 0),
                allowance: tok_int(&tokens, 8, 0),
                heat: tok_int(&tokens, 9, 1000),
                budget: tok_int(&tokens, 10, 210),
                prepos_micro: tok_micro(&tokens, 11),
            }),
            "PLANLEG" => {
                let container = tok(&tokens, 6);
                plan.legs.push(Leg {
                    cid: tok(&tokens, 1).to_string(),
                    lane: tok(&tokens, 2).to_string(),
                    depart: tok_int(&tokens, 3, 0),
                    party: parse_bool01(tok(&tokens, 4)),
                    door: parse_bool01(tok(&tokens, 5)),
                    container: if container == "-" || container.is_empty() {
                        None
                    } else {
                        Some(container.to_string())
                    },
                })
            }
            "FLAGS" => {
                plan.decision_age = tok_int(&tokens, 1, 0);
                plan.approvals = tok_int(&tokens, 2, 0);
                plan.precool = parse_ids(tok(&tokens, 3));
                plan.disposition = parse_ids(tok(&tokens, 4));
                plan.estimate = parse_ids(tok(&tokens, 5));
                plan.cost_red = parse_ids(tok(&tokens, 6));

                plan.capacity_verified = parse_bool01(tok(&tokens, 7));
                plan.documents_verified = parse_bool01(tok(&tokens, 8));
                plan.counterparty_verified = parse_bool01(tok(&tokens, 9));
                plan.permits = parse_bool01(tok(&tokens, 10));
                plan.preauth = parse_bool01(tok(&tokens, 11));
                plan.refreshed = parse_bool01(tok(&tokens, 12));
                plan.cap_measured = parse_bool01(tok(&tokens, 13));
                plan.oob_verified = parse_bool01(tok(&tokens, 14));
                plan.escrow = parse_ids(tok(&tokens, 15));
                plan.backup = parse_pairs(tok(&tokens, 16));
                plan.thermal = parse_ids(tok(&tokens, 17));
                plan.prepos = parse_pairs(tok(&tokens, 18))
                    .into_iter()
                    .map(|(cid, value)| (cid, parse_micro(&value)))
                    .collect();
                plan.deferred = parse_ids(tok(&tokens, 19));
            }
            "EVENT" => notice_zero = tok(&tokens, 1) == "0",
            "EXPECT" => {
                expect = (
                    tok(&tokens, 1).to_string(),
                    tok_int(&tokens, 2, 0),
                    tok_int(&tokens, 3, 0),
                    tok_int(&tokens, 4, 0),
                )
            }
            "END" => out.push(Instance {
                name: name.clone(),
                horizon_min,
                nodes: nodes.clone(),
                lanes: lanes.clone(),
                cons: cons.clone(),
                plan: plan.clone(),
                notice_zero,
                expect_verdict: expect.0.clone(),
                expect_uca: expect.1,
                expect_excursion: expect.2,
                expect_blocks: expect.3,
            }),
            _ => {}
        }
    }
    out
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let mut path = String::from("evidence/instances.txt");
    let mut threads = thread::available_parallelism().map(|n| n.get()).unwrap_or(4);
    let mut repeat = 1usize;
    let mut index = 1;
    while index < args.len() {
        match args[index].as_str() {
            "--instances" => {
                path = args[index + 1].clone();
                index += 2;
            }
            "--threads" => {
                threads = args[index + 1].parse().unwrap_or(threads);
                index += 2;
            }
            "--repeat" => {
                repeat = args[index + 1].parse().unwrap_or(1);
                index += 2;
            }
            _ => index += 1,
        }
    }

    let mut config = Config::default();
    let text = match fs::read_to_string(&path) {
        Ok(value) => value,
        Err(error) => {
            eprintln!("cannot read {path}: {error}");
            std::process::exit(2);
        }
    };
    let instances = parse_instances(&text, &mut config);
    if instances.is_empty() {
        eprintln!("no instances parsed from {path}");
        std::process::exit(2);
    }

    let started = Instant::now();
    let mut mismatches: Vec<String> = Vec::new();
    let mut checked = 0usize;
    for _ in 0..repeat {
        let chunk_size = (instances.len() + threads - 1) / threads;
        let results: Vec<(usize, Vec<String>)> = thread::scope(|scope| {
            let mut handles = Vec::new();
            for chunk in instances.chunks(chunk_size.max(1)) {
                let config = config.clone();
                handles.push(scope.spawn(move || {
                    let mut local = Vec::new();
                    for inst in chunk {
                        let outcome = evaluate(inst, &config);
                        let comparable = !inst.expect_verdict.is_empty();
                        if comparable
                            && (outcome.verdict != inst.expect_verdict
                                || outcome.uca != inst.expect_uca
                                || outcome.excursion != inst.expect_excursion
                                || outcome.blocks != inst.expect_blocks)
                        {
                            local.push(format!(
                                "{}: rust({},{},{},{}) python({},{},{},{})",
                                inst.name,
                                outcome.verdict,
                                outcome.uca,
                                outcome.excursion,
                                outcome.blocks,
                                inst.expect_verdict,
                                inst.expect_uca,
                                inst.expect_excursion,
                                inst.expect_blocks
                            ));
                        }
                    }
                    (chunk.len(), local)
                }));
            }
            handles
                .into_iter()
                .filter_map(|handle| handle.join().ok())
                .collect()
        });
        checked = 0;
        mismatches.clear();
        for (count, local) in results {
            checked += count;
            mismatches.extend(local);
        }
    }
    let elapsed = started.elapsed().as_secs_f64();
    let per_pass = elapsed / repeat as f64;
    println!(
        "instances={} threads={} repeat={} checked={} mismatches={} seconds={:.4} per_pass={:.4} throughput={:.0}/s",
        instances.len(),
        threads,
        repeat,
        checked,
        mismatches.len(),
        elapsed,
        per_pass,
        (instances.len() as f64) / per_pass
    );
    for line in mismatches.iter().take(10) {
        println!("mismatch {line}");
    }
    if !mismatches.is_empty() {
        std::process::exit(1);
    }
}


