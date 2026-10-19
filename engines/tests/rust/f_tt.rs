//! Contracts shared by F's paired-bound and single-bound TT experiments.
//!
//! These exercise the production Table, including its publication protocol.
//! Search convergence and the move witness are tested separately in search.rs.
use super::*;

fn control() -> Control {
    Control::new(&Limits { depth: 8, nodes: 0, movetime: None })
}

fn entry(key: u64, lower: i32, upper: i32, depth: u8) -> Entry {
    Entry { key, mv: Move { from: 119, to: 0, promo: 5 }, depth, lower, upper }
}

fn assert_record(actual: Entry, expected: Entry) {
    assert_eq!(actual.key, expected.key, "the complete position key must match");
    assert_eq!(actual.mv, expected.mv, "move must come from the same publication");
    assert_eq!(actual.depth, expected.depth);
    assert_eq!((actual.lower, actual.upper), (expected.lower, expected.upper));
}

#[test]
fn slot_storage_matches_the_selected_memory_experiment() {
    #[cfg(rove_f_single)]
    let bytes = 16;
    #[cfg(not(rove_f_single))]
    let bytes = 24;
    assert_eq!(std::mem::size_of::<Slot>(), bytes);
    let table = Table::new(8);
    assert_eq!(table.slots.len(), 256);
    assert_eq!(std::mem::size_of_val(table.slots.as_slice()), 256 * bytes);
}

#[test]
fn all_key_bits_and_zero_key_survive_colliding_slot_replacements() {
    let table = Table::new(8);
    let c = control();
    // All keys index slot zero. In particular, the high bit is key data and
    // must not be consumed as an occupancy marker or silently truncated.
    let keys = [0, 1 << 8, 1 << 31, 1 << 32, 1 << 47, 1 << 63,
        (1 << 63) | (1 << 8), u64::MAX & !255];
    for (i, &key) in keys.iter().enumerate() {
        let expected = entry(key, 37 * i as i32 - 101, 37 * i as i32 - 101, 17);
        assert!(table.put(expected, 0, &c));
        assert_record(table.get(key, 0).expect("the uncontended write must be readable"), expected);
        for &other in &keys {
            if other != key { assert!(table.get(other, 0).is_none(), "colliding key {other:016x} accepted {key:016x}"); }
        }
    }
    assert_eq!(c.conflicts.load(Ordering::Relaxed), 0);
}

#[test]
fn exact_lower_upper_and_ordering_only_entries_keep_their_meaning() {
    let table = Table::new(8);
    let c = control();
    for (lower, upper) in [(0, 0), (179, 179), (-217, -217),
        (-411, INF), (732, INF), (-INF, -179), (-INF, 411), (-INF, INF)] {
        table.clear();
        let expected = entry(0x8000_0000_0000_0042, lower, upper, 63);
        assert!(table.get(expected.key, 0).is_none());
        assert!(table.put(expected, 0, &c));
        assert_record(table.get(expected.key, 0).unwrap(), expected);
        table.clear();
        assert!(table.get(expected.key, 0).is_none(), "clear must invalidate an ordering-only entry too");
    }
}

#[test]
fn seven_bit_depth_and_promotion_fields_round_trip_without_score_overlap() {
    let table = Table::new(8);
    let c = control();
    for depth in [0, 1, 63, 64, 95, 96, 126, 127] {
        for promo in [0, 2, 3, 4, 5] {
            table.clear();
            let mut expected = entry(0x9040_2000_1000_0007, -12345, -12345, depth);
            expected.mv = Move { from: 0, to: 119, promo };
            assert!(table.put(expected, 0, &c));
            assert_record(table.get(expected.key, 0).unwrap(), expected);
        }
    }
}

#[test]
fn mate_scores_are_relative_to_the_query_ply_in_every_bound_direction() {
    let table = Table::new(8);
    let c = control();
    for store_ply in [0, 1, 37, 95] {
        for query_ply in [0, 1, 42, 95] {
            for value in [MATE - 5, -MATE + 5] {
                // A positive mate becomes farther away at a deeper query ply;
                // a negative mate becomes closer. This expected value follows
                // mate distance semantics, independently of the packed layout.
                let adjusted = value + value.signum() * (store_ply as i32 - query_ply as i32);
                for direction in 0..3 {
                    table.clear();
                    let (lower, upper) = match direction { 0 => (value, value), 1 => (value, INF), _ => (-INF, value) };
                    let stored = entry(0x8000_0040_0000_0053, lower, upper, 95);
                    assert!(table.put(stored, store_ply, &c));
                    assert_record(table.get(stored.key, store_ply).unwrap(), stored);
                    let loaded = table.get(stored.key, query_ply).unwrap();
                    assert_eq!(loaded.key, stored.key);
                    assert_eq!(loaded.mv, stored.mv);
                    assert_eq!(loaded.depth, stored.depth);
                    match direction {
                        0 => assert_eq!((loaded.lower, loaded.upper), (adjusted, adjusted)),
                        1 => {
                            assert_eq!(loaded.lower, adjusted);
                            assert!(loaded.upper > MATE + 128, "an unbounded upper edge must stay outside all possible search scores");
                        }
                        _ => {
                            assert!(loaded.lower < -MATE - 128, "an unbounded lower edge must stay outside all possible search scores");
                            assert_eq!(loaded.upper, adjusted);
                        }
                    }
                }
            }
        }
    }
}

#[test]
fn invalid_interval_is_rejected_without_destroying_an_existing_record() {
    let table = Table::new(8);
    let c = control();
    let valid = entry(0x500, 17, 17, 6);
    assert!(table.put(valid, 0, &c));
    assert!(!table.put(Entry { lower: 19, upper: 18, ..valid }, 0, &c));
    assert_eq!(c.conflicts.load(Ordering::Relaxed), 1);
    assert_record(table.get(valid.key, 0).unwrap(), valid);
}

#[cfg(rove_f_single)]
#[test]
fn opposite_bound_replacement_never_invents_an_exact_score_or_keeps_a_false_witness() {
    let table = Table::new(8);
    let c = control();
    let lower = entry(0x517, 120, INF, 4);
    let upper = Entry { mv: Move { from: 3, to: 19, promo: 0 }, lower: -INF, upper: 120, ..lower };
    assert!(table.put(lower, 0, &c));
    assert_record(table.get(lower.key, 0).unwrap(), lower);
    assert!(table.put(upper, 0, &c));
    assert_record(table.get(upper.key, 0).unwrap(), upper);
    assert!(table.put(lower, 0, &c));
    assert_record(table.get(lower.key, 0).unwrap(), lower);
    // The format carries one bound. Dropping an upper bound from a finite
    // interval is conservative; returning the interval as exact would not be.
    assert!(table.put(Entry { lower: 110, upper: 130, ..lower }, 0, &c));
    assert_record(table.get(lower.key, 0).unwrap(), Entry { lower: 110, ..lower });
    assert_eq!(c.conflicts.load(Ordering::Relaxed), 0);
}

#[cfg(rove_f_single)]
#[test]
fn held_publication_lock_hides_a_synthetic_mixed_key_payload_and_skips_writers() {
    let table = Table::new(8);
    let c = control();
    let old = entry(0x8000_0000_0000_0039, -71, -71, 2);
    let next = entry(0x4000_0000_0000_0039, 223, 223, 7);
    assert!(table.put(old, 0, &c));
    let slot = &table.slots[old.key as usize & table.mask];
    assert!(slot.acquire());
    // Simulate the middle of the real exclusive publication: the new key is
    // visible in storage but the payload still belongs to the previous key.
    // Direct mutation is confined to the held production lock.
    unsafe { *slot.key.get() = next.key; }
    assert!(table.get(old.key, 0).is_none());
    assert!(table.get(next.key, 0).is_none());
    assert!(table.put(next, 0, &c), "contention is an admitted skipped write");
    unsafe { *slot.key.get() = old.key; }
    slot.release();
    assert_record(table.get(old.key, 0).unwrap(), old);
    assert!(table.get(next.key, 0).is_none());
    assert!(table.put(next, 0, &c));
    assert_record(table.get(next.key, 0).unwrap(), next);
    assert!(table.get(old.key, 0).is_none());
}

// Each key has a fixed, independently derived tuple. Competing writers all
// target the same slot; successful reads must never combine any two tuples.
fn stress_entry(key: u64) -> Entry {
    let signature = key.rotate_left(17).wrapping_mul(0x9e37_79b9_7f4a_7c15) ^ key;
    let score = (signature % 20001) as i32 - 10000;
    Entry { key, mv: Move { from: (signature & 7) as u8,
        to: 112 + ((signature >> 3) & 7) as u8,
        promo: [0, 2, 3, 4, 5][((signature >> 6) % 5) as usize] },
        depth: ((signature >> 11) & 127) as u8, lower: score, upper: score }
}

#[test]
fn eight_colliding_writers_only_publish_complete_full_key_score_move_tuples() {
    let table = Arc::new(Table::new(8));
    let c = Arc::new(control());
    let barrier = Arc::new(std::sync::Barrier::new(8));
    let accepted = AtomicU64::new(0);
    std::thread::scope(|scope| {
        for worker in 0..8u64 {
            let table = table.clone();
            let c = c.clone();
            let barrier = barrier.clone();
            let accepted = &accepted;
            scope.spawn(move || {
                barrier.wait();
                let mut observed = 0;
                for turn in 0..12000u64 {
                    let key = ((worker & 1) << 63) | (((worker >> 1) + 1) << 48)
                        | ((turn & 15) << 8) | 0x2d;
                    let expected = stress_entry(key);
                    assert!(table.put(expected, 0, &c));
                    if let Some(actual) = table.get(key, 0) {
                        assert_record(actual, expected);
                        observed += 1;
                    }
                    if turn & 255 == 0 { std::thread::yield_now(); }
                }
                accepted.fetch_add(observed, Ordering::Relaxed);
            });
        }
    });
    assert!(accepted.load(Ordering::Relaxed) > 0, "stress must actually observe published records");
    assert_eq!(c.conflicts.load(Ordering::Relaxed), 0);
    table.clear();
    let final_entry = stress_entry(0x8004_0000_0000_0f2d);
    assert!(table.put(final_entry, 0, &c));
    assert_record(table.get(final_entry.key, 0).unwrap(), final_entry);
}
