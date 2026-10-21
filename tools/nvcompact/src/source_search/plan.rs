//! Lazy, deterministic coverage of a finite generated choice set.
//!
//! Source edits are expressed against one immutable basis. Compatible edits
//! commute; conflicting alternatives are rejected by the composer, not by a
//! length or individual-cost heuristic. No exponential list is allocated.
use num_bigint::BigUint;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Order {
    SubsetsOnly,
    Interleaved,
    SinglesOnly,
}

pub(super) enum Work {
    Single(usize),
    Subset(Vec<usize>),
}

/// Two lazy lanes share a deterministic round-robin. A losing singleton never
/// removes its edits from the subset lane. A phase may pause this cursor and
/// resume it without restarting the enumeration or keeping an exponential list.
pub(super) struct WorkQueue {
    single: usize,
    count: usize,
    subsets: Combinations,
    single_turn: bool,
}

impl WorkQueue {
    pub(super) fn new(count: usize, order: Order) -> Self {
        Self {
            single: if order == Order::SubsetsOnly {
                count
            } else {
                0
            },
            count,
            subsets: Combinations::new(if order == Order::SinglesOnly {
                0
            } else {
                count
            }),
            single_turn: true,
        }
    }

    pub(super) fn pending(&self) -> bool {
        self.single < self.count || self.subsets.next.is_some()
    }

    pub(super) fn pending_subsets(&self) -> bool {
        self.subsets.next.is_some()
    }

    pub(super) fn available(&self, subsets_allowed: bool) -> bool {
        self.single < self.count || subsets_allowed && self.pending_subsets()
    }

    pub(super) fn next(&mut self, subsets_allowed: bool) -> Option<Work> {
        if self.single < self.count
            && (self.single_turn || !subsets_allowed || !self.pending_subsets())
        {
            let index = self.single;
            self.single += 1;
            self.single_turn = false;
            Some(Work::Single(index))
        } else if subsets_allowed {
            self.single_turn = true;
            self.subsets.next().map(Work::Subset)
        } else {
            None
        }
    }
}

pub(super) struct Combinations {
    count: usize,
    next: Option<Vec<usize>>,
}

impl Combinations {
    pub(super) fn new(count: usize) -> Self {
        Self {
            count,
            next: (count >= 2).then(|| vec![0, 1]),
        }
    }

    pub(super) fn cardinality(count: usize) -> String {
        Self::unvisited(count, 0)
    }

    pub(super) fn unvisited(count: usize, attempted: usize) -> String {
        ((BigUint::from(1u8) << count) - BigUint::from(count + 1) - BigUint::from(attempted))
            .to_string()
    }
}

impl Iterator for Combinations {
    type Item = Vec<usize>;

    fn next(&mut self) -> Option<Self::Item> {
        let result = self.next.take()?;
        let width = result.len();
        let mut following = result.clone();
        if let Some(pivot) = (0..width)
            .rev()
            .find(|&i| following[i] < self.count - width + i)
        {
            following[pivot] += 1;
            for i in pivot + 1..width {
                following[i] = following[i - 1] + 1;
            }
            self.next = Some(following);
        } else if width < self.count {
            self.next = Some((0..width + 1).collect());
        }
        Some(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn interleaves_losing_singles_and_subsets_and_can_resume_either_lane() {
        let mut plan = WorkQueue::new(4, Order::Interleaved);
        assert!(matches!(plan.next(true), Some(Work::Single(0))));
        assert!(matches!(plan.next(true), Some(Work::Subset(v)) if v == vec![0, 1]));
        assert!(matches!(plan.next(true), Some(Work::Single(1))));
        assert!(matches!(plan.next(true), Some(Work::Subset(v)) if v == vec![0, 2]));
        assert!(matches!(plan.next(false), Some(Work::Single(2))));
        assert!(matches!(plan.next(false), Some(Work::Single(3))));
        assert!(!plan.available(false));
        assert!(plan.pending());
        assert!(matches!(plan.next(true), Some(Work::Subset(v)) if v == vec![0, 3]));
        let mut remaining = 0;
        while plan.next(true).is_some() {
            remaining += 1;
        }
        assert_eq!(remaining, 8);
        assert!(!plan.pending());
        let mut singles = WorkQueue::new(2, Order::SinglesOnly);
        assert!(matches!(singles.next(true), Some(Work::Single(0))));
        assert!(matches!(singles.next(true), Some(Work::Single(1))));
        assert!(!singles.pending());
    }

    #[test]
    fn visits_each_nontrivial_subset_without_materializing_the_power_set() {
        let actual: Vec<_> = Combinations::new(4).collect();
        assert_eq!(
            actual,
            vec![
                vec![0, 1],
                vec![0, 2],
                vec![0, 3],
                vec![1, 2],
                vec![1, 3],
                vec![2, 3],
                vec![0, 1, 2],
                vec![0, 1, 3],
                vec![0, 2, 3],
                vec![1, 2, 3],
                vec![0, 1, 2, 3]
            ]
        );
        assert_eq!(Combinations::cardinality(4), actual.len().to_string());
        assert_eq!(Combinations::new(0).count(), 0);
        assert_eq!(Combinations::new(1).count(), 0);
        assert_eq!(
            Combinations::new(512).take(2).collect::<Vec<_>>(),
            vec![vec![0, 1], vec![0, 2]]
        );
        assert!(Combinations::cardinality(512).len() > 150);
    }
}
