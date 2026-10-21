//! Lazy, deterministic coverage of a finite generated choice set.
//!
//! Source edits are expressed against one immutable basis. Compatible edits
//! commute; conflicting alternatives are rejected by the composer, not by a
//! length or individual-cost heuristic. No exponential list is allocated.
use num_bigint::BigUint;

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
        ((BigUint::from(1u8) << count) - BigUint::from(count + 1)).to_string()
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
