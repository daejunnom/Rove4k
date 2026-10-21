//! A conservative integer domain shared by flow facts and diagnostic reports.
//! Intervals, known bits and optional finite sets are intersected, never treated
//! as independent evidence. A finite set is a containing set, not reachability.
use serde::{Deserialize, Serialize};
use std::sync::Arc;

pub(crate) const FINITE_LIMIT: usize = 4096;

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct DomainSummary {
    pub minimum: String,
    pub maximum: String,
    pub bits: u32,
    pub signed: bool,
    pub known_zero: String,
    pub known_one: String,
    /// When present this is the complete conservative set at the site.
    /// Larger sets omit this display list; finite_cardinality/values_omitted
    /// distinguish that case from an unenumerated domain.
    pub values: Option<Vec<String>>,
    #[serde(default)]
    pub finite_cardinality: Option<usize>,
    #[serde(default)]
    pub values_omitted: usize,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct Domain {
    pub lo: i128,
    pub hi: i128,
    pub bits: u32,
    pub signed: bool,
    pub zero: u64,
    pub one: u64,
    values: Option<Arc<Vec<i128>>>,
}

fn mask(bits: u32) -> u64 {
    u64::MAX >> (64 - bits)
}

impl Domain {
    pub fn from_summary(summary: &DomainSummary) -> Option<Self> {
        let bits = summary.bits;
        if !(1..=64).contains(&bits) {
            return None;
        }
        let lo: i128 = summary.minimum.parse().ok()?;
        let hi: i128 = summary.maximum.parse().ok()?;
        let type_lo = if summary.signed {
            -(1i128 << (bits - 1))
        } else {
            0
        };
        let type_hi = if summary.signed {
            (1i128 << (bits - 1)) - 1
        } else {
            (1i128 << bits) - 1
        };
        if lo > hi || lo < type_lo || hi > type_hi {
            return None;
        }
        let zero = u64::from_str_radix(summary.known_zero.strip_prefix("0x")?, 16).ok()?;
        let one = u64::from_str_radix(summary.known_one.strip_prefix("0x")?, 16).ok()?;
        if (zero | one) & !mask(bits) != 0 || zero & one != 0 {
            return None;
        }
        let mut result = Self::interval(lo, hi, bits, summary.signed);
        if !result.restrict_bits(zero, one) {
            return None;
        }
        if let Some(values) = &summary.values {
            if values.is_empty() || values.len() > FINITE_LIMIT {
                return None;
            }
            let mut values: Vec<i128> = values
                .iter()
                .map(|v| v.parse().ok())
                .collect::<Option<_>>()?;
            if values.iter().any(|&v| !result.contains(v)) {
                return None;
            }
            values.sort_unstable();
            values.dedup();
            result.values = Some(Arc::new(values));
        }
        Some(result)
    }
    pub fn interval(lo: i128, hi: i128, bits: u32, signed: bool) -> Self {
        debug_assert!(lo <= hi && (1..=64).contains(&bits));
        let mut result = Self {
            lo,
            hi,
            bits,
            signed,
            zero: 0,
            one: 0,
            values: None,
        };
        result.reduce_interval_bits();
        result
    }

    pub fn from_values(mut values: Vec<i128>, bits: u32, signed: bool) -> Option<Self> {
        values.sort_unstable();
        values.dedup();
        let (&lo, &hi) = (values.first()?, values.last()?);
        let mut result = Self::interval(lo, hi, bits, signed);
        let mut zero = mask(bits);
        let mut one = mask(bits);
        for &value in &values {
            let raw = value as u64 & mask(bits);
            zero &= !raw;
            one &= raw;
        }
        result.zero |= zero;
        result.one |= one;
        if values.len() <= FINITE_LIMIT {
            result.values = Some(Arc::new(values));
        }
        Some(result)
    }

    fn reduce_interval_bits(&mut self) {
        // A signed interval crossing zero crosses the bit-pattern discontinuity.
        if self.lo < 0 && self.hi >= 0 {
            return;
        }
        let lo = self.lo as u64 & mask(self.bits);
        let hi = self.hi as u64 & mask(self.bits);
        let differing = lo ^ hi;
        let fixed = if differing == 0 {
            mask(self.bits)
        } else {
            u64::MAX
                .checked_shl(64 - differing.leading_zeros())
                .unwrap_or(0)
                & mask(self.bits)
        };
        self.one |= lo & fixed;
        self.zero |= !lo & fixed;
    }

    pub fn contains(&self, value: i128) -> bool {
        let raw = value as u64 & mask(self.bits);
        value >= self.lo
            && value <= self.hi
            && raw & self.zero == 0
            && raw & self.one == self.one
            && self
                .values
                .as_ref()
                .is_none_or(|v| v.binary_search(&value).is_ok())
    }

    pub fn restrict_interval(&mut self, lo: i128, hi: i128) -> bool {
        self.lo = self.lo.max(lo);
        self.hi = self.hi.min(hi);
        if self.lo > self.hi {
            return false;
        }
        self.reduce_interval_bits();
        self.reduce_values()
    }

    pub fn restrict_bits(&mut self, zero: u64, one: u64) -> bool {
        self.zero |= zero & mask(self.bits);
        self.one |= one & mask(self.bits);
        self.zero & self.one == 0 && self.reduce_values()
    }

    fn reduce_values(&mut self) -> bool {
        if self.zero & self.one != 0 {
            return false;
        }
        if let Some(values) = self.values.take() {
            let mut values = Arc::try_unwrap(values).unwrap_or_else(|v| (*v).clone());
            values.retain(|&v| self.contains(v));
            if values.is_empty() {
                return false;
            }
            self.lo = values[0];
            self.hi = *values.last().unwrap();
            self.values = Some(Arc::new(values));
        } else if let Some(values) = self.enumerate(FINITE_LIMIT) {
            if values.is_empty() {
                return false;
            }
            self.lo = values[0];
            self.hi = *values.last().unwrap();
            self.values = Some(Arc::new(values));
        }
        self.reduce_interval_bits();
        true
    }

    pub fn union(&self, other: &Self) -> Self {
        debug_assert_eq!((self.bits, self.signed), (other.bits, other.signed));
        let mut result = Self::interval(
            self.lo.min(other.lo),
            self.hi.max(other.hi),
            self.bits,
            self.signed,
        );
        result.zero |= self.zero & other.zero;
        result.one |= self.one & other.one;
        if let (Some(mut a), Some(b)) =
            (self.enumerate(FINITE_LIMIT), other.enumerate(FINITE_LIMIT))
        {
            a.extend(b);
            a.sort_unstable();
            a.dedup();
            if a.len() <= FINITE_LIMIT {
                result.values = Some(Arc::new(a));
            }
        }
        result
    }

    pub fn enumerate(&self, limit: usize) -> Option<Vec<i128>> {
        if let Some(values) = &self.values {
            return (values.len() <= limit).then(|| (**values).clone());
        }
        if self.hi.checked_sub(self.lo)?.checked_add(1)? <= limit as i128 {
            return Some((self.lo..=self.hi).filter(|&v| self.contains(v)).collect());
        }
        let unknown = mask(self.bits) & !(self.zero | self.one);
        let count = 1usize.checked_shl(unknown.count_ones())?;
        if count > limit {
            return None;
        }
        let positions: Vec<_> = (0..self.bits)
            .filter(|i| unknown & (1u64 << i) != 0)
            .collect();
        let mut values = Vec::with_capacity(count);
        for index in 0..count {
            let mut raw = self.one;
            for (j, &position) in positions.iter().enumerate() {
                if index & (1usize << j) != 0 {
                    raw |= 1u64 << position;
                }
            }
            let value = if self.signed && raw & (1u64 << (self.bits - 1)) != 0 {
                raw as i128 - (1i128 << self.bits)
            } else {
                raw as i128
            };
            if self.contains(value) {
                values.push(value);
            }
        }
        values.sort_unstable();
        Some(values)
    }

    pub fn summary(&self) -> DomainSummary {
        let values = self.enumerate(FINITE_LIMIT);
        let cardinality = values.as_ref().map(Vec::len);
        let omitted = cardinality.filter(|&n| n > 256).unwrap_or(0);
        DomainSummary {
            minimum: self.lo.to_string(),
            maximum: self.hi.to_string(),
            bits: self.bits,
            signed: self.signed,
            known_zero: format!("0x{:x}", self.zero),
            known_one: format!("0x{:x}", self.one),
            values: values
                .filter(|v| v.len() <= 256)
                .map(|v| v.into_iter().map(|x| x.to_string()).collect()),
            finite_cardinality: cardinality,
            values_omitted: omitted,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sparse_branches_keep_holes_and_join_only_reachable_values() {
        let mut board = Domain::interval(0, 127, 32, true);
        assert!(board.restrict_bits(0x88, 0));
        let values = board.enumerate(128).unwrap();
        assert_eq!(values.len(), 64);
        assert!(values.contains(&119));
        assert!(!values.contains(&8));
        let a = Domain::from_values(vec![1, 9], 32, true).unwrap();
        let b = Domain::from_values(vec![3, 11], 32, true).unwrap();
        assert_eq!(a.union(&b).enumerate(4).unwrap(), vec![1, 3, 9, 11]);
        let mut all = Domain::interval(i32::MIN as i128, i32::MAX as i128, 32, true);
        assert!(all.restrict_bits(0x88, 0));
        assert!(all.contains(256));
        assert!(all.contains(-256));
        assert!(all.enumerate(FINITE_LIMIT).is_none());
    }

    #[test]
    fn signed_bit_intervals_and_budgeted_enumeration_are_conservative() {
        for (lo, hi) in [
            (-128, -1),
            (-1, 1),
            (0, 255),
            (16, 31),
            (i32::MIN as i128, -1),
        ] {
            let d = Domain::interval(lo, hi, 32, true);
            for v in [lo, hi, lo + (hi - lo) / 2] {
                assert!(d.contains(v));
            }
        }
        let mut d = Domain::interval(0, u64::MAX as i128, 64, false);
        assert!(d.restrict_bits(!0x8000000000000001, 0));
        assert_eq!(
            d.enumerate(4).unwrap(),
            vec![0, 1, 1i128 << 63, (1i128 << 63) + 1]
        );
        assert!(d.enumerate(3).is_none());
        assert!(!d.restrict_bits(1, 1));
    }
}
