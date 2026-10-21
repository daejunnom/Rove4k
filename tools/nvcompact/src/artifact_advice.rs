//! Read-only repeated-byte inventory for a final artifact. Matching bytes are
//! not evidence of a C constant, an instruction boundary, or a safe rewrite.
//! This module never decodes, loads, executes, or modifies the inspected file.
use anyhow::{ensure, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::cmp::Ordering;
use std::collections::BinaryHeap;
use std::mem::size_of;

const MAX_INPUT_BYTES: usize = 4 << 20;
const MAX_FINDINGS: usize = 1024;
const MAX_OFFSETS: usize = 256;

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct ArtifactAdviceOptions {
    pub word_bytes: usize,
    pub max_findings: usize,
    pub max_offsets: usize,
    pub max_input_bytes: usize,
}

impl Default for ArtifactAdviceOptions {
    fn default() -> Self {
        Self {
            word_bytes: 8,
            max_findings: 128,
            max_offsets: 64,
            max_input_bytes: MAX_INPUT_BYTES,
        }
    }
}

impl ArtifactAdviceOptions {
    fn validate(&self) -> Result<()> {
        ensure!(
            matches!(self.word_bytes, 4 | 8),
            "word_bytes must be 4 or 8"
        );
        ensure!(
            (1..=MAX_FINDINGS).contains(&self.max_findings),
            "max_findings must be 1..{MAX_FINDINGS}"
        );
        ensure!(
            (1..=MAX_OFFSETS).contains(&self.max_offsets),
            "max_offsets must be 1..{MAX_OFFSETS}"
        );
        ensure!(
            (1..=MAX_INPUT_BYTES).contains(&self.max_input_bytes),
            "max_input_bytes must be 1..{MAX_INPUT_BYTES}"
        );
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct Group {
    start: usize,
    end: usize,
    word: u64,
    padding: bool,
}

impl Group {
    fn count(self) -> usize {
        self.end - self.start
    }
}

// Better findings compare smaller: non-padding, more occurrences, then bytes
// in lexical order. The heap's maximum is the worst currently retained group.
impl Ord for Group {
    fn cmp(&self, other: &Self) -> Ordering {
        self.padding
            .cmp(&other.padding)
            .then_with(|| other.count().cmp(&self.count()))
            .then_with(|| self.word.cmp(&other.word))
            .then_with(|| self.start.cmp(&other.start))
            .then_with(|| self.end.cmp(&other.end))
    }
}

impl PartialOrd for Group {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

/// Inspect every byte offset, including unaligned and overlapping windows.
/// The sorted index uses at most 4 MiB * 16 bytes on supported hosts. Only a
/// bounded heap of group descriptors and bounded reported offsets are retained;
/// discovering many repeated patterns does not allocate one object per group.
pub fn inspect(data: &[u8], options: &ArtifactAdviceOptions) -> Result<Value> {
    options.validate()?;
    ensure!(
        data.len() <= options.max_input_bytes,
        "artifact exceeds max_input_bytes ({})",
        options.max_input_bytes
    );
    let width = options.word_bytes;
    let windows = data.len().checked_sub(width).map_or(0, |n| n + 1);
    let mut index = Vec::<(u64, u32)>::new();
    index
        .try_reserve_exact(windows)
        .context("could not allocate bounded artifact index")?;
    for (offset, bytes) in data.windows(width).enumerate() {
        let word = if width == 8 {
            u64::from_be_bytes(bytes.try_into().expect("eight-byte window"))
        } else {
            u64::from(u32::from_be_bytes(
                bytes.try_into().expect("four-byte window"),
            ))
        };
        // The validated input bound is smaller than u32::MAX.
        index.push((word, offset as u32));
    }
    index.sort_unstable();

    let padding_ones = if width == 8 {
        u64::MAX
    } else {
        u64::from(u32::MAX)
    };
    let mut retained = BinaryHeap::<Group>::with_capacity(options.max_findings);
    let mut repeated_groups = 0usize;
    let mut start = 0usize;
    while start < index.len() {
        let word = index[start].0;
        let mut end = start + 1;
        while end < index.len() && index[end].0 == word {
            end += 1;
        }
        if end - start >= 2 {
            repeated_groups += 1;
            let group = Group {
                start,
                end,
                word,
                padding: word == 0 || word == padding_ones,
            };
            if retained.len() < options.max_findings {
                retained.push(group);
            } else if retained.peek().is_some_and(|worst| group < *worst) {
                *retained.peek_mut().expect("nonempty bounded heap") = group;
            }
        }
        start = end;
    }

    let mut findings = Vec::with_capacity(retained.len());
    for group in retained.into_sorted_vec() {
        let bytes = group.word.to_be_bytes();
        let bytes = &bytes[8 - width..];
        let little = bytes
            .iter()
            .enumerate()
            .fold(0u64, |word, (i, byte)| word | (u64::from(*byte) << (i * 8)));
        let occurrences = &index[group.start..group.end];
        let offsets: Vec<_> = occurrences
            .iter()
            .take(options.max_offsets)
            .map(|(_, offset)| *offset)
            .collect();
        let mut non_overlapping = 0usize;
        let mut next_available = 0usize;
        for &(_, offset) in occurrences {
            let offset = offset as usize;
            if non_overlapping == 0 || offset >= next_available {
                non_overlapping += 1;
                next_available = offset + width;
            }
        }
        findings.push(json!({
            "kind":"repeated_bytes",
            "bytes_hex":hex::encode(bytes),
            "little_endian_hex":format!("0x{little:0digits$x}", digits=width * 2),
            "big_endian_hex":format!("0x{:0digits$x}", group.word, digits=width * 2),
            "occurrences":group.count(),
            "non_overlapping_occurrences":non_overlapping,
            "offsets":offsets,
            "offsets_truncated":group.count() > options.max_offsets,
            "padding_like":group.padding,
            "semantic_constant":null,
            "estimated_savings_bytes":null
        }));
    }
    Ok(json!({
        "schema":"nvcompact-artifact-advice-v1",
        "advisory_only":true,
        "input_sha256":crate::sha256(data),
        "input_bytes":data.len(),
        "options":options,
        "scan":{
            "complete":true,
            "windows":windows,
            "alignment":"every byte offset; overlapping windows included",
            "index_allocation_bytes":index.capacity() * size_of::<(u64, u32)>(),
            "memory_scope":"sorted index plus bounded finding descriptors and offsets; excludes caller input, allocator bookkeeping and JSON report storage"
        },
        "repeated_groups":repeated_groups,
        "omitted_groups":repeated_groups - findings.len(),
        "ordering":"non-padding first, occurrence count descending, byte pattern ascending",
        "scope":"exact raw byte patterns only; no decoding, instruction/section interpretation, semantic constant proof, execution or source modification",
        "guidance":"Trace a repeated pattern to its source and inspect type, layout and consumers before proposing reuse. Measure the complete rebuilt artifact separately; repeated bytes do not establish removable storage or savings.",
        "findings":findings
    }))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn inventories_unaligned_magic_and_endianness_without_mutation() {
        let mut data = vec![0x91];
        data.extend_from_slice(&0x5555_5555_5555_5555u64.to_le_bytes());
        data.extend_from_slice(&[0x82, 0x73]);
        data.extend_from_slice(&0x5555_5555_5555_5555u64.to_le_bytes());
        let original = data.clone();
        let report = inspect(&data, &ArtifactAdviceOptions::default()).unwrap();
        let magic = report["findings"]
            .as_array()
            .unwrap()
            .iter()
            .find(|f| f["bytes_hex"] == "5555555555555555")
            .unwrap();
        assert_eq!(magic["offsets"], json!([1, 11]));
        assert_eq!(magic["non_overlapping_occurrences"], 2);
        assert_eq!(magic["padding_like"], false);
        assert_eq!(data, original);
        let options = ArtifactAdviceOptions {
            word_bytes: 4,
            ..Default::default()
        };
        let report = inspect(&[1, 2, 3, 4, 9, 1, 2, 3, 4], &options).unwrap();
        let finding = &report["findings"][0];
        assert_eq!(finding["bytes_hex"], "01020304");
        assert_eq!(finding["big_endian_hex"], "0x01020304");
        assert_eq!(finding["little_endian_hex"], "0x04030201");
    }

    #[test]
    fn counts_overlaps_and_reports_bounded_offsets_and_groups() {
        let options = ArtifactAdviceOptions {
            word_bytes: 4,
            max_findings: 1,
            max_offsets: 2,
            ..Default::default()
        };
        let mut data = vec![0; 40];
        data.extend_from_slice(&[0x55; 8]);
        let report = inspect(&data, &options).unwrap();
        let findings = report["findings"].as_array().unwrap();
        assert_eq!(findings.len(), 1);
        // The numerous zero windows are lower priority than the useful mask.
        assert_eq!(findings[0]["bytes_hex"], "55555555");
        assert_eq!(findings[0]["occurrences"], 5);
        assert_eq!(findings[0]["non_overlapping_occurrences"], 2);
        assert_eq!(findings[0]["offsets"], json!([40, 41]));
        assert_eq!(findings[0]["offsets_truncated"], true);
        assert_eq!(report["repeated_groups"], 2);
        assert_eq!(report["omitted_groups"], 1);

        let padding = inspect(&[0xff; 12], &options).unwrap();
        assert_eq!(padding["findings"][0]["padding_like"], true);
        assert_eq!(padding["findings"][0]["occurrences"], 9);
        assert_eq!(padding["findings"][0]["non_overlapping_occurrences"], 3);
    }

    #[test]
    fn bounds_and_short_inputs_are_explicit() {
        for width in [0, 1, 7, 16] {
            assert!(inspect(
                b"abcdefghi",
                &ArtifactAdviceOptions {
                    word_bytes: width,
                    ..Default::default()
                }
            )
            .is_err());
        }
        assert!(inspect(
            b"12345",
            &ArtifactAdviceOptions {
                max_input_bytes: 4,
                ..Default::default()
            }
        )
        .is_err());
        assert!(inspect(
            b"",
            &ArtifactAdviceOptions {
                max_input_bytes: MAX_INPUT_BYTES + 1,
                ..Default::default()
            }
        )
        .is_err());
        assert!(inspect(
            b"",
            &ArtifactAdviceOptions {
                max_offsets: MAX_OFFSETS + 1,
                ..Default::default()
            }
        )
        .is_err());
        for input in [b"".as_slice(), b"1234567"] {
            let report = inspect(input, &ArtifactAdviceOptions::default()).unwrap();
            assert_eq!(report["scan"]["windows"], 0);
            assert_eq!(report["repeated_groups"], 0);
            assert_eq!(report["scan"]["complete"], true);
        }
    }
}
