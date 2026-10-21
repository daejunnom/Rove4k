//! Whole-file cost ownership for inspected source envelopes.
//!
//! Source identity, codec work, header derivation, and the final artifact are
//! different boundaries. Only successful byte-roundtrip codec work is cached.
//! The cache is local to one objective and never uses a native ELF as the key
//! for a source-bearing submission. Independent regeneration bypasses it.
use crate::{
    codec::{self, CodecPortfolio, Recipe},
    envelope::best_header,
    process, sha256,
};
use anyhow::{ensure, Context, Result};
use serde::Serialize;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{
    collections::hash_map::RandomState,
    hash::{BuildHasher, Hash},
    mem::size_of,
    sync::{mpsc, Arc},
    thread::{Scope, ScopedJoinHandle},
};

/// Retained allocation budgets, separate from active codec scratch memory.
/// Entries include their vector storage, owned key strings and encoded bytes.
/// Allocator bookkeeping, the inspected input/configuration, caller-owned
/// reports, one current best artifact, and at most `jobs` active codec workers
/// (including their compression scratch and 64 KiB restoration buffer) are
/// outside these budgets. Ordered result windows permit at most `4 * jobs`
/// entries; additional header + encoded buffers beyond `jobs` are capped at 16 MiB
/// by conservative per-result output bounds. These are allocation budgets, not
/// a process RSS limit.
#[derive(Clone, Copy, Debug, Serialize)]
pub struct CacheBudget {
    pub max_bytes: usize,
    pub max_entries: usize,
    pub max_header_bytes: usize,
    pub max_header_entries: usize,
}

impl Default for CacheBudget {
    fn default() -> Self {
        Self {
            max_bytes: 64 << 20,
            max_entries: 4096,
            max_header_bytes: 1 << 20,
            max_header_entries: 16,
        }
    }
}

impl CacheBudget {
    pub fn disabled() -> Self {
        Self {
            max_bytes: 0,
            max_entries: 0,
            max_header_bytes: 0,
            max_header_entries: 0,
        }
    }

    fn validate(&self) -> Result<()> {
        ensure!(
            self.max_bytes <= 512 << 20 && self.max_entries <= 65_536,
            "codec cache exceeds 512 MiB / 65536-entry profile"
        );
        ensure!(
            self.max_header_bytes <= 16 << 20 && self.max_header_entries <= 256,
            "header cache exceeds 16 MiB / 256-entry profile"
        );
        Ok(())
    }
}

#[derive(Clone, Debug, Default, Serialize)]
pub struct CostStats {
    pub measurements: usize,
    /// One execution includes compression and bounded restoration comparison.
    pub codec_executions: usize,
    pub codec_cache_hits: usize,
    pub codec_failures: usize,
    pub codec_not_started: usize,
    pub header_derivations: usize,
    pub header_cache_hits: usize,
    pub header_failures: usize,
    pub fresh_measurements: usize,
    pub fresh_codec_executions: usize,
    pub fresh_codec_failures: usize,
    pub fresh_codec_not_started: usize,
    pub fresh_header_derivations: usize,
    pub fresh_header_failures: usize,
    pub codec_cache_entries: usize,
    pub codec_cache_bytes: usize,
    pub codec_cache_peak_bytes: usize,
    pub codec_cache_evictions: usize,
    pub codec_cache_skipped: usize,
    pub header_cache_entries: usize,
    pub header_cache_bytes: usize,
    pub header_cache_peak_bytes: usize,
    pub header_cache_evictions: usize,
    pub header_cache_skipped: usize,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Reuse {
    Allowed,
    Fresh,
}

trait CacheIdentity: Eq + Hash {
    fn owned_key_bytes(&self) -> usize;
}

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
struct CodecKey {
    payload: [u8; 32],
    payload_bytes: usize,
    recipe: Recipe,
}

impl CacheIdentity for CodecKey {
    fn owned_key_bytes(&self) -> usize {
        self.recipe.format.capacity() + self.recipe.check.as_ref().map_or(0, String::capacity)
    }
}

impl CacheIdentity for String {
    fn owned_key_bytes(&self) -> usize {
        self.capacity()
    }
}

const NO_SLOT: usize = usize::MAX;

struct CacheEntry<K> {
    key: K,
    bytes: Arc<[u8]>,
    owned_bytes: usize,
    previous: usize,
    next: usize,
    bucket: usize,
}

/// A bounded, indexed FIFO. Slot and bucket allocations are charged before
/// admission. Slots form a ring, so eviction never moves all retained keys.
/// Hash collisions still compare the complete typed key. Declaration-ordered
/// admission determines retention independently of worker completion order.
struct BoundedBytesCache<K> {
    entries: Vec<Option<CacheEntry<K>>>,
    buckets: Vec<usize>,
    hash_builder: RandomState,
    head: usize,
    len: usize,
    max_bytes: usize,
    owned_bytes: usize,
    peak_bytes: usize,
    evictions: usize,
    skipped: usize,
}

impl<K: CacheIdentity> BoundedBytesCache<K> {
    fn new(max_bytes: usize, max_entries: usize) -> Self {
        // The bucket count is the next power of two above 2 * capacity, hence
        // less than 4 * capacity. Reserve room for useful byte storage too.
        let capacity = max_entries
            .min(max_bytes / (size_of::<Option<CacheEntry<K>>>() + 4 * size_of::<usize>() + 32));
        let mut entries = Vec::with_capacity(capacity);
        entries.resize_with(capacity, || None);
        let buckets = if capacity == 0 {
            Vec::new()
        } else {
            vec![NO_SLOT; (2 * capacity).next_power_of_two()]
        };
        let owned_bytes = entries.capacity() * size_of::<Option<CacheEntry<K>>>()
            + buckets.capacity() * size_of::<usize>();
        Self {
            entries,
            buckets,
            hash_builder: RandomState::new(),
            head: 0,
            len: 0,
            max_bytes,
            owned_bytes,
            peak_bytes: owned_bytes,
            evictions: 0,
            skipped: 0,
        }
    }

    fn slot(&self, key: &K) -> Option<usize> {
        if self.buckets.is_empty() {
            return None;
        }
        let bucket = self.hash_builder.hash_one(key) as usize & (self.buckets.len() - 1);
        let mut slot = self.buckets[bucket];
        while slot != NO_SLOT {
            let entry = self.entries[slot].as_ref().expect("occupied cache link");
            if entry.key == *key {
                return Some(slot);
            }
            slot = entry.next;
        }
        None
    }

    fn get(&self, key: &K) -> Option<Arc<[u8]>> {
        self.slot(key).map(|slot| {
            Arc::clone(
                &self.entries[slot]
                    .as_ref()
                    .expect("occupied cache slot")
                    .bytes,
            )
        })
    }

    fn evict(&mut self) {
        let removed = self.entries[self.head].take().expect("occupied FIFO head");
        if removed.previous == NO_SLOT {
            self.buckets[removed.bucket] = removed.next;
        } else {
            self.entries[removed.previous].as_mut().unwrap().next = removed.next;
        }
        if removed.next != NO_SLOT {
            self.entries[removed.next].as_mut().unwrap().previous = removed.previous;
        }
        self.head = (self.head + 1) % self.entries.len();
        self.len -= 1;
        self.owned_bytes -= removed.owned_bytes;
        self.evictions += 1;
    }

    fn insert(&mut self, key: K, bytes: Arc<[u8]>) {
        if self.slot(&key).is_some() {
            return;
        }
        // Arc's two counters plus aligned byte storage, and actual owned String
        // capacities. Preallocated slots and buckets are already charged.
        let arc_bytes = bytes.len().next_multiple_of(size_of::<usize>()) + 2 * size_of::<usize>();
        let owned_bytes = key.owned_key_bytes() + arc_bytes;
        let metadata_bytes = self.entries.capacity() * size_of::<Option<CacheEntry<K>>>()
            + self.buckets.capacity() * size_of::<usize>();
        if self.entries.is_empty() || metadata_bytes + owned_bytes > self.max_bytes {
            self.skipped += 1;
            return;
        }
        while self.len == self.entries.len() || self.owned_bytes + owned_bytes > self.max_bytes {
            self.evict();
        }
        let bucket = self.hash_builder.hash_one(&key) as usize & (self.buckets.len() - 1);
        let next = self.buckets[bucket];
        let slot = (self.head + self.len) % self.entries.len();
        if next != NO_SLOT {
            self.entries[next].as_mut().unwrap().previous = slot;
        }
        self.entries[slot] = Some(CacheEntry {
            key,
            bytes,
            owned_bytes,
            previous: NO_SLOT,
            next,
            bucket,
        });
        self.buckets[bucket] = slot;
        self.len += 1;
        self.owned_bytes += owned_bytes;
        self.peak_bytes = self.peak_bytes.max(self.owned_bytes);
        debug_assert!(self.owned_bytes <= self.max_bytes);
    }
}

struct ArtifactCandidate {
    recipe: Recipe,
    header: Arc<[u8]>,
    packed: Arc<[u8]>,
    codec_evaluation: &'static str,
    header_evaluation: &'static str,
}

impl ArtifactCandidate {
    fn bytes(&self) -> usize {
        self.header.len() + self.packed.len()
    }

    fn artifact(&self) -> Vec<u8> {
        let mut data = Vec::with_capacity(self.bytes());
        data.extend_from_slice(&self.header);
        data.extend_from_slice(&self.packed);
        data
    }

    fn record(
        &self,
        id: &str,
        payload_hash: &str,
        payload_bytes: usize,
        equivalence: &str,
    ) -> Result<Value> {
        let record_id = sha256(&serde_json::to_vec(&json!([id, self.recipe]))?)[..16].to_owned();
        let mut hash = Sha256::new();
        hash.update(&self.header);
        hash.update(&self.packed);
        Ok(json!({
            "id":record_id,"variant":id,"recipe":self.recipe,"bytes":self.bytes(),
            "header_bytes":self.header.len(),"packed_bytes":self.packed.len(),
            "source_bytes":payload_bytes,"sha256":hex::encode(hash.finalize()),
            "payload_sha256":payload_hash,"equivalence":equivalence,
            "cost_evaluation":{"codec":self.codec_evaluation,"header":self.header_evaluation}
        }))
    }
}

struct BatchEvaluation {
    records: Vec<Value>,
    sizes: Vec<usize>,
    best: ArtifactCandidate,
}

pub struct PortfolioEvaluation {
    pub records: Vec<Value>,
    pub best: Value,
    pub data: Vec<u8>,
    pub coverage: Value,
}

/// One objective owns the inspected envelope, finite recipe policy, worker
/// budget and disposable measurement caches. It neither generates source nor
/// validates C semantics or the external shell decoder.
pub struct WholeFileObjective {
    header: Vec<u8>,
    old_decoder: String,
    portfolio: CodecPortfolio,
    jobs: usize,
    budget: CacheBudget,
    codec_cache: BoundedBytesCache<CodecKey>,
    header_cache: BoundedBytesCache<String>,
    stats: CostStats,
}

impl WholeFileObjective {
    pub fn new(
        header: &[u8],
        old_decoder: &str,
        portfolio: CodecPortfolio,
        jobs: usize,
        budget: CacheBudget,
    ) -> Result<Self> {
        ensure!((1..=16).contains(&jobs), "codec jobs must be 1..16");
        ensure!(
            !header.is_empty() && header.len() <= 4 << 20 && header.ends_with(b"\n"),
            "inspected header must end in a newline and fit the 4 MiB profile"
        );
        ensure!(!old_decoder.is_empty(), "empty inspected decoder");
        budget.validate()?;
        // Validate the inspected envelope once, using the same derivation code
        // as every candidate. Reuse this successful result if its spelling is
        // requested later; the original header itself remains immutable.
        let unchanged = best_header(header, old_decoder, old_decoder)?;
        let mut header_cache =
            BoundedBytesCache::new(budget.max_header_bytes, budget.max_header_entries);
        header_cache.insert(old_decoder.to_owned(), Arc::from(unchanged));
        Ok(Self {
            header: header.to_vec(),
            old_decoder: old_decoder.to_owned(),
            portfolio,
            jobs,
            budget,
            codec_cache: BoundedBytesCache::new(budget.max_bytes, budget.max_entries),
            header_cache,
            stats: CostStats {
                header_derivations: 1,
                ..CostStats::default()
            },
        })
    }

    pub fn context(&self) -> Value {
        json!({
            "kind":"inspected-envelope-codec-portfolio-v1",
            "inspected_header_sha256":sha256(&self.header),
            "inspected_header_bytes":self.header.len(),"inspected_decoder":self.old_decoder,
            "codec_portfolio":self.portfolio.context(),"codecs":codec::library_versions(),
            "jobs":self.jobs,"cache_budget":self.budget,
            "cache_scope":"one objective; payload SHA-256 and length plus complete typed recipe; successful compression and byte restoration only",
            "memory_scope":"cache budgets include slot/bucket allocations; exclude allocator metadata, immutable input, caller reports, one best artifact and jobs active codec workers; each decoder comparison uses at most 64 KiB output scratch; ordered windows have at most 4*jobs results with at most 16 MiB conservative extra header+encoded-output allowance beyond jobs; window keys/channels/tuple metadata are additional bounded overhead",
            "worker_schedule":"available workers claim the next declared cache miss inside a bounded ordered window; results and cache admission retain declaration order",
            "cost_scope":"entire inspected header plus entire encoded source payload; no native-ELF merging",
            "fresh_evaluation":"bypass all retained codec/header measurements and regenerate the requested recipe domain"
        })
    }

    pub fn stats(&self) -> CostStats {
        CostStats {
            codec_cache_entries: self.codec_cache.len,
            codec_cache_bytes: self.codec_cache.owned_bytes,
            codec_cache_peak_bytes: self.codec_cache.peak_bytes,
            codec_cache_evictions: self.codec_cache.evictions,
            codec_cache_skipped: self.codec_cache.skipped,
            header_cache_entries: self.header_cache.len,
            header_cache_bytes: self.header_cache.owned_bytes,
            header_cache_peak_bytes: self.header_cache.peak_bytes,
            header_cache_evictions: self.header_cache.evictions,
            header_cache_skipped: self.header_cache.skipped,
            ..self.stats.clone()
        }
    }

    pub fn measure(&mut self, payload: &[u8]) -> Result<usize> {
        Ok(self
            .portfolio_batch(
                "source-cost",
                payload,
                "candidate only",
                Reuse::Allowed,
                false,
            )?
            .0
            .best
            .bytes())
    }

    /// Re-evaluate the full current portfolio, including fresh adaptive seed
    /// selection. This is stronger than merely recompressing the prior winner.
    pub fn fresh_measure(&mut self, payload: &[u8]) -> Result<usize> {
        Ok(self
            .portfolio_batch(
                "source-cost",
                payload,
                "candidate only",
                Reuse::Fresh,
                false,
            )?
            .0
            .best
            .bytes())
    }

    /// A recipe-specific strategy uses the same byte restoration, header and
    /// cache boundary as the full portfolio, without building a JSON record or
    /// concatenating a whole artifact merely to obtain its cost.
    pub fn measure_recipe(&mut self, payload: &[u8], recipe: &Recipe) -> Result<usize> {
        self.recipe_cost(payload, recipe, Reuse::Allowed)
    }

    pub fn fresh_measure_recipe(&mut self, payload: &[u8], recipe: &Recipe) -> Result<usize> {
        self.recipe_cost(payload, recipe, Reuse::Fresh)
    }

    fn recipe_cost(&mut self, payload: &[u8], recipe: &Recipe, reuse: Reuse) -> Result<usize> {
        let hash = payload_digest(payload)?;
        Ok(self
            .batch(
                "source-cost",
                payload,
                &hash,
                "candidate only",
                std::slice::from_ref(recipe),
                reuse,
                false,
            )?
            .best
            .bytes())
    }

    pub fn evaluate(
        &mut self,
        id: &str,
        payload: &[u8],
        equivalence: &str,
    ) -> Result<PortfolioEvaluation> {
        self.evaluate_portfolio(id, payload, equivalence, Reuse::Allowed)
    }

    pub fn fresh_evaluate(
        &mut self,
        id: &str,
        payload: &[u8],
        equivalence: &str,
    ) -> Result<PortfolioEvaluation> {
        self.evaluate_portfolio(id, payload, equivalence, Reuse::Fresh)
    }

    pub fn evaluate_recipe(
        &mut self,
        id: &str,
        payload: &[u8],
        equivalence: &str,
        recipe: &Recipe,
    ) -> Result<(Value, Vec<u8>)> {
        self.one_recipe(id, payload, equivalence, recipe, Reuse::Allowed)
    }

    pub fn fresh_evaluate_recipe(
        &mut self,
        id: &str,
        payload: &[u8],
        equivalence: &str,
        recipe: &Recipe,
    ) -> Result<(Value, Vec<u8>)> {
        self.one_recipe(id, payload, equivalence, recipe, Reuse::Fresh)
    }

    fn one_recipe(
        &mut self,
        id: &str,
        payload: &[u8],
        equivalence: &str,
        recipe: &Recipe,
        reuse: Reuse,
    ) -> Result<(Value, Vec<u8>)> {
        let hash = payload_digest(payload)?;
        let result = self.batch(
            id,
            payload,
            &hash,
            equivalence,
            std::slice::from_ref(recipe),
            reuse,
            false,
        )?;
        Ok((
            result
                .best
                .record(id, &hex::encode(hash), payload.len(), equivalence)?,
            result.best.artifact(),
        ))
    }

    fn evaluate_portfolio(
        &mut self,
        id: &str,
        payload: &[u8],
        equivalence: &str,
        reuse: Reuse,
    ) -> Result<PortfolioEvaluation> {
        let (result, coverage) = self.portfolio_batch(id, payload, equivalence, reuse, true)?;
        Ok(PortfolioEvaluation {
            best: result
                .best
                .record(id, &sha256(payload), payload.len(), equivalence)?,
            data: result.best.artifact(),
            records: result.records,
            coverage,
        })
    }

    fn portfolio_batch(
        &mut self,
        id: &str,
        payload: &[u8],
        equivalence: &str,
        reuse: Reuse,
        records: bool,
    ) -> Result<(BatchEvaluation, Value)> {
        let hash = payload_digest(payload)?;
        let plan = self.portfolio.plan(payload.len());
        let mut result = self.batch(
            id,
            payload,
            &hash,
            equivalence,
            &plan.initial,
            reuse,
            records,
        )?;
        let refinements = self.portfolio.refinement_recipes(&plan, &result.sizes)?;
        if !refinements.is_empty() {
            let mut refined = self.batch(
                id,
                payload,
                &hash,
                equivalence,
                &refinements,
                reuse,
                records,
            )?;
            for record in &mut refined.records {
                record["phase"] = json!("match-finder-refinement");
            }
            result.records.extend(refined.records);
            result.sizes.extend(refined.sizes);
            if refined.best.bytes() < result.best.bytes() {
                result.best = refined.best;
            }
        }
        // Scalar cost callers do not consume coverage or recipe JSON. Keep
        // that allocation on the report-producing boundary, while preserving
        // the exact evaluated recipe domain and all measurement statistics.
        let coverage = if records {
            json!({
                "policy":self.portfolio.context(),"initial_recipes":plan.initial.len(),
                "refinement_recipes":refinements.len(),"completed_recipe_requests":result.sizes.len(),
                "complete":true,"fresh":reuse == Reuse::Fresh,
                "scope":"complete declared initial domain and the policy-selected refinements; no global compression optimum"
            })
        } else {
            Value::Null
        };
        Ok((result, coverage))
    }

    fn header_for(&mut self, recipe: &Recipe, reuse: Reuse) -> Result<(Arc<[u8]>, &'static str)> {
        let decoder = codec::decoder_for(recipe)?;
        if reuse == Reuse::Allowed {
            if let Some(header) = self.header_cache.get(&decoder) {
                self.stats.header_cache_hits += 1;
                return Ok((header, "cache_hit"));
            }
            self.stats.header_derivations += 1;
        } else {
            self.stats.fresh_header_derivations += 1;
        }
        let bytes = best_header(&self.header, &self.old_decoder, &decoder)?;
        // Allowed decoder and tail-offset substitutions are far below 128
        // extra bytes. Check the allowance before retaining a derived header.
        ensure!(
            bytes.len() <= self.header.len() + 128,
            "derived header exceeds scheduler allowance"
        );
        let header = Arc::from(bytes);
        if reuse == Reuse::Allowed {
            self.header_cache.insert(decoder, Arc::clone(&header));
        }
        Ok((
            header,
            if reuse == Reuse::Fresh {
                "fresh"
            } else {
                "executed"
            },
        ))
    }

    #[allow(clippy::too_many_arguments)]
    fn batch(
        &mut self,
        id: &str,
        payload: &[u8],
        payload_hash: &[u8; 32],
        equivalence: &str,
        recipes: &[Recipe],
        reuse: Reuse,
        emit_records: bool,
    ) -> Result<BatchEvaluation> {
        ensure!(!recipes.is_empty(), "empty codec batch");
        let mut records = Vec::new();
        let mut sizes = Vec::with_capacity(recipes.len());
        let mut best: Option<ArtifactCandidate> = None;
        let payload_hash_text = emit_records.then(|| hex::encode(payload_hash));

        // Keep admission and ties ordered while workers dynamically take the
        // next cache miss. Extra lookahead is limited both by count and by a
        // conservative encoded-output allowance, so large payloads do not
        // multiply retained result memory merely to improve scheduling.
        let window = codec_window(self.jobs, payload.len(), self.header.len() + 128);
        // The same scoped workers serve every window; cache-only batches and
        // the serial path do not create threads.
        std::thread::scope(|scope| {
            let mut workers = None;
            let outcome = (|| {
                for chunk in recipes.chunks(window) {
                    ensure!(!process::cancelled(), "cancelled before codec batch");
                    let mut pending = Vec::with_capacity(chunk.len());
                    for recipe in chunk {
                        if reuse == Reuse::Allowed {
                            self.stats.measurements += 1;
                        } else {
                            self.stats.fresh_measurements += 1;
                        }
                        let (header, header_evaluation) = match self.header_for(recipe, reuse) {
                            Ok(header) => header,
                            Err(error) => {
                                if reuse == Reuse::Allowed {
                                    self.stats.header_failures += 1;
                                } else {
                                    self.stats.fresh_header_failures += 1;
                                }
                                return Err(error);
                            }
                        };
                        let key = CodecKey {
                            payload: *payload_hash,
                            payload_bytes: payload.len(),
                            recipe: recipe.clone(),
                        };
                        let cached = if reuse == Reuse::Allowed {
                            self.codec_cache.get(&key)
                        } else {
                            None
                        };
                        pending.push((key, header, header_evaluation, cached));
                    }

                    let requests: Vec<_> = pending
                        .iter()
                        .map(|(key, _, _, cached)| cached.is_none().then_some(&key.recipe))
                        .collect();
                    let results = if requests.iter().any(Option::is_some) {
                        workers
                            .get_or_insert_with(|| {
                                CodecWorkers::new(scope, payload, self.jobs.min(recipes.len()))
                            })
                            .measure(&requests)
                    } else {
                        (0..requests.len()).map(|_| None).collect()
                    };

                    let mut failure = None;
                    for ((key, header, header_evaluation, cached), result) in
                        pending.into_iter().zip(results)
                    {
                        let (packed, codec_evaluation) = if let Some(cached) = cached {
                            self.stats.codec_cache_hits += 1;
                            (cached, "cache_hit")
                        } else {
                            let outcome = result.context("codec worker returned no result")?;
                            match (reuse, outcome.executed) {
                                (Reuse::Allowed, true) => self.stats.codec_executions += 1,
                                (Reuse::Fresh, true) => self.stats.fresh_codec_executions += 1,
                                (Reuse::Allowed, false) => self.stats.codec_not_started += 1,
                                (Reuse::Fresh, false) => self.stats.fresh_codec_not_started += 1,
                            }
                            match outcome.result {
                                Ok(packed) => (
                                    packed,
                                    if reuse == Reuse::Fresh {
                                        "fresh"
                                    } else {
                                        "executed"
                                    },
                                ),
                                Err(error) => {
                                    if reuse == Reuse::Allowed {
                                        self.stats.codec_failures += 1;
                                    } else {
                                        self.stats.fresh_codec_failures += 1;
                                    }
                                    if failure.is_none() {
                                        failure = Some(error);
                                    }
                                    continue;
                                }
                            }
                        };
                        if reuse == Reuse::Allowed && codec_evaluation != "cache_hit" {
                            self.codec_cache.insert(key.clone(), Arc::clone(&packed));
                        }
                        let candidate = ArtifactCandidate {
                            recipe: key.recipe,
                            header,
                            packed,
                            codec_evaluation,
                            header_evaluation,
                        };
                        sizes.push(candidate.bytes());
                        if emit_records {
                            records.push(candidate.record(
                                id,
                                payload_hash_text.as_deref().expect("requested record hash"),
                                payload.len(),
                                equivalence,
                            )?);
                        }
                        if best
                            .as_ref()
                            .is_none_or(|previous| candidate.bytes() < previous.bytes())
                        {
                            best = Some(candidate);
                        }
                    }
                    if let Some(error) = failure {
                        return Err(error);
                    }
                }
                Ok(())
            })();
            let joined = workers.map_or(Ok(()), CodecWorkers::finish);
            outcome.and(joined)
        })?;
        ensure!(sizes.len() == recipes.len(), "codec batch omitted a recipe");
        Ok(BatchEvaluation {
            records,
            sizes,
            best: best.context("no measured codec candidates")?,
        })
    }
}

/// Extra complete header + compressed results may use at most this much
/// beyond the original jobs-sized window. Both output bounds are checked
/// before retention, including fresh/disabled-cache header allocations.
const LOOKAHEAD_BYTES: usize = 16 << 20;

fn codec_window(jobs: usize, payload_bytes: usize, header_bound: usize) -> usize {
    if jobs == 1 {
        return 1;
    }
    let output_bound = payload_bytes
        .saturating_mul(2)
        .saturating_add(65536)
        .saturating_add(header_bound);
    jobs + (3 * jobs).min(LOOKAHEAD_BYTES / output_bound)
}

struct CodecOutcome {
    executed: bool,
    result: Result<Arc<[u8]>>,
}

impl CodecOutcome {
    fn not_started(message: &str) -> Self {
        Self {
            executed: false,
            result: Err(anyhow::anyhow!("{message}")),
        }
    }
}

struct Completion {
    worker: usize,
    index: usize,
    outcome: CodecOutcome,
}

struct CodecWorker<'scope> {
    input: mpsc::SyncSender<(usize, Recipe)>,
    handle: ScopedJoinHandle<'scope, ()>,
}

/// A batch owns all workers, a bounded request channel per worker, and one
/// bounded completion channel. Each worker has at most one outstanding task.
/// Completions schedule more work immediately; the caller later consumes the
/// bounded window in declaration order. All workers are joined on every exit.
struct CodecWorkers<'scope> {
    payload: &'scope [u8],
    workers: Vec<CodecWorker<'scope>>,
    output: mpsc::Receiver<Completion>,
}

impl<'scope> CodecWorkers<'scope> {
    fn new<'env>(scope: &'scope Scope<'scope, 'env>, payload: &'scope [u8], jobs: usize) -> Self {
        let mut workers = Vec::new();
        let (replies, output) = mpsc::sync_channel(jobs);
        if jobs > 1 {
            for worker in 0..jobs {
                let (input, requests) = mpsc::sync_channel::<(usize, Recipe)>(1);
                let replies = replies.clone();
                let handle = scope.spawn(move || {
                    while let Ok((index, recipe)) = requests.recv() {
                        // A panic must produce a completion too; otherwise a
                        // shared reply channel could wait forever while live
                        // siblings are idle waiting for their next requests.
                        let outcome =
                            std::panic::catch_unwind(|| compress_roundtrip(payload, &recipe))
                                .unwrap_or_else(|_| CodecOutcome {
                                    executed: true,
                                    result: Err(anyhow::anyhow!("codec worker panicked")),
                                });
                        if replies
                            .send(Completion {
                                worker,
                                index,
                                outcome,
                            })
                            .is_err()
                        {
                            break;
                        }
                    }
                });
                workers.push(CodecWorker { input, handle });
            }
        }
        Self {
            payload,
            workers,
            output,
        }
    }

    fn measure(&self, requests: &[Option<&Recipe>]) -> Vec<Option<CodecOutcome>> {
        if self.workers.is_empty() {
            return requests
                .iter()
                .map(|recipe| recipe.map(|recipe| compress_roundtrip(self.payload, recipe)))
                .collect();
        }
        let mut results: Vec<_> = (0..requests.len()).map(|_| None).collect();
        let mut remaining = requests
            .iter()
            .enumerate()
            .filter_map(|(index, recipe)| recipe.map(|recipe| (index, recipe)));
        let dispatch = |worker: usize,
                        remaining: &mut dyn Iterator<Item = (usize, &Recipe)>,
                        results: &mut [Option<CodecOutcome>]|
         -> bool {
            for (index, recipe) in remaining {
                if self.workers[worker]
                    .input
                    .send((index, recipe.clone()))
                    .is_ok()
                {
                    return true;
                }
                results[index] = Some(CodecOutcome::not_started(
                    "codec worker disconnected before request",
                ));
            }
            false
        };
        let mut active = 0;
        for worker in 0..self.workers.len() {
            active += usize::from(dispatch(worker, &mut remaining, &mut results));
        }
        while active != 0 {
            match self.output.recv() {
                Ok(Completion {
                    worker,
                    index,
                    outcome,
                }) => {
                    active -= 1;
                    results[index] = Some(outcome);
                    active += usize::from(dispatch(worker, &mut remaining, &mut results));
                }
                Err(_) => {
                    for (index, recipe) in requests.iter().enumerate() {
                        if recipe.is_some() && results[index].is_none() {
                            results[index] = Some(CodecOutcome::not_started(
                                "codec workers disconnected before result",
                            ));
                        }
                    }
                    break;
                }
            }
        }
        results
    }

    fn finish(self) -> Result<()> {
        let mut handles = Vec::with_capacity(self.workers.len());
        for CodecWorker { input, handle } in self.workers {
            drop(input);
            handles.push(handle);
        }
        drop(self.output);
        let mut failure = None;
        for handle in handles {
            if handle.join().is_err() && failure.is_none() {
                failure = Some(anyhow::anyhow!("codec worker panicked"));
            }
        }
        match failure {
            Some(error) => Err(error),
            None => Ok(()),
        }
    }
}

fn payload_digest(payload: &[u8]) -> Result<[u8; 32]> {
    ensure!(
        payload.len() <= codec::MAX_PAYLOAD,
        "source payload exceeds bounded codec objective profile"
    );
    Ok(Sha256::digest(payload).into())
}

fn compress_roundtrip(payload: &[u8], recipe: &Recipe) -> CodecOutcome {
    if process::cancelled() {
        return CodecOutcome::not_started("cancelled before codec candidate");
    }
    CodecOutcome {
        executed: true,
        result: (|| {
            let packed = codec::compress(payload, recipe)?;
            ensure!(
                packed.len() <= payload.len().saturating_mul(2).saturating_add(65536),
                "encoded result exceeds bounded scheduler output profile"
            );
            codec::verify_decode(&packed, recipe, payload)?;
            Ok(Arc::from(packed))
        })(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // This is inert input data. No submitted shell, compiler or engine runs.
    const HEADER: &[u8] = b"#!/bin/sh\ntail -n+3 \"$0\"|gzip -d\n";

    fn gzip(level: u32) -> Recipe {
        let mut recipe = Recipe::new("gzip");
        recipe.level = Some(level);
        recipe
    }

    fn objective(recipes: Vec<Recipe>, jobs: usize, budget: CacheBudget) -> WholeFileObjective {
        WholeFileObjective::new(
            HEADER,
            "gzip -d",
            CodecPortfolio::fixed(recipes).unwrap(),
            jobs,
            budget,
        )
        .unwrap()
    }

    #[test]
    fn indexed_fifo_handles_collisions_wraparound_and_oversize_entries() {
        // Force every key into one bucket to exercise collision-chain removal
        // across ring wraparound independently of the hash function's choices.
        #[derive(PartialEq, Eq)]
        struct Collision(u32);
        impl Hash for Collision {
            fn hash<H: std::hash::Hasher>(&self, state: &mut H) {
                0u8.hash(state);
            }
        }
        impl CacheIdentity for Collision {
            fn owned_key_bytes(&self) -> usize {
                0
            }
        }
        let mut cache = BoundedBytesCache::new(4096, 3);
        for index in 0..30 {
            let bytes: Arc<[u8]> = Arc::from(vec![index as u8; 19]);
            cache.insert(Collision(index), Arc::clone(&bytes));
            cache.insert(Collision(index), Arc::from(vec![255; 19]));
            assert_eq!(cache.len, (index as usize + 1).min(3));
            assert!(cache.owned_bytes <= cache.max_bytes);
            for query in 0..=index {
                let found = cache.get(&Collision(query));
                if query + 3 <= index {
                    assert!(found.is_none());
                } else {
                    assert_eq!(found.as_deref(), Some(vec![query as u8; 19].as_slice()));
                }
            }
        }
        let retained = cache.get(&Collision(29)).unwrap();
        cache.insert(Collision(100), Arc::from(vec![0; 4096]));
        assert_eq!(cache.skipped, 1);
        assert_eq!(cache.evictions, 27);
        assert_eq!(cache.get(&Collision(29)).unwrap(), retained);
        assert_eq!(retained.as_ref(), &[29; 19]);
    }

    #[test]
    fn worker_lookahead_is_bounded_by_count_and_output_allowance() {
        for jobs in 1..=16 {
            for bytes in [0, 1024, 65536, 1 << 20, codec::MAX_PAYLOAD] {
                for header in [256, (4 << 20) + 128] {
                    let window = codec_window(jobs, bytes, header);
                    assert!((jobs..=4 * jobs).contains(&window));
                    assert!((window - jobs) * (2 * bytes + 65536 + header) <= LOOKAHEAD_BYTES);
                    if jobs == 1 {
                        assert_eq!(window, 1);
                    }
                }
            }
        }
    }

    #[test]
    fn source_identity_cache_and_fresh_portfolio_are_distinct() {
        let first = b"int main(){return 0;}\n";
        // A source-cost objective never asks whether these compile identically.
        let second = b"int main(){return 0;} /* same native could be produced */\n";
        let mut cost = objective(vec![gzip(1), gzip(9)], 2, CacheBudget::default());
        let original = cost.evaluate("first", first, "fixture bytes").unwrap();
        let before = cost.stats();
        assert_eq!(before.codec_executions, 2);
        assert_eq!(cost.measure(first).unwrap(), original.data.len());
        assert_eq!(cost.stats().codec_cache_hits, 2);
        cost.measure(second).unwrap();
        assert_eq!(cost.stats().codec_executions, 4);
        let fresh = cost
            .fresh_evaluate("first", first, "fixture bytes")
            .unwrap();
        assert_eq!(fresh.data, original.data);
        assert_eq!(fresh.best["id"], original.best["id"]);
        assert_eq!(cost.stats().codec_cache_hits, 2);
        assert_eq!(cost.stats().fresh_codec_executions, 2);
        assert_eq!(cost.stats().fresh_header_derivations, 2);
        assert_eq!(fresh.coverage["complete"], true);
        assert_eq!(
            fresh.coverage["policy"]["exhaustive_declared_recipe_domain"],
            true
        );
    }

    #[test]
    fn cache_budget_and_failure_never_create_fake_success() {
        let budget = CacheBudget {
            max_bytes: 512,
            max_entries: 1,
            max_header_bytes: 128,
            max_header_entries: 1,
        };
        let mut cost = objective(vec![gzip(1), gzip(9)], 2, budget);
        for payload in [b"first".as_slice(), b"different", b"third"] {
            cost.measure(payload).unwrap();
            assert!(cost.stats().codec_cache_bytes <= budget.max_bytes);
            assert!(cost.stats().codec_cache_entries <= budget.max_entries);
            assert!(cost.stats().header_cache_bytes <= budget.max_header_bytes);
        }
        assert!(cost.stats().codec_cache_evictions > 0);
        let mut broken = Recipe::new("alone");
        broken.preset = Some(u32::MAX);
        for _ in 0..2 {
            assert!(cost
                .evaluate_recipe("bad", b"fixture", "fixture bytes", &broken)
                .is_err());
        }
        assert_eq!(cost.stats().codec_failures, 2);
        assert_eq!(cost.stats().codec_cache_hits, 0);
        // A failing worker must also be joined while a sibling's successful
        // byte-roundtrip may be reused. The bad recipe must execute again.
        let mut parallel_failure = objective(vec![gzip(1), broken], 2, CacheBudget::default());
        for _ in 0..2 {
            assert!(parallel_failure.measure(b"fixture").is_err());
        }
        assert_eq!(parallel_failure.stats().codec_failures, 2);
        assert_eq!(parallel_failure.stats().codec_executions, 3);
        assert_eq!(parallel_failure.stats().codec_cache_hits, 1);
        assert_eq!(parallel_failure.stats().codec_cache_entries, 1);
        let before = cost.stats();
        cost.fresh_measure(b"first").unwrap();
        assert_eq!(cost.stats().codec_executions, before.codec_executions);
        assert_eq!(cost.stats().codec_cache_hits, before.codec_cache_hits);
        assert_eq!(cost.stats().fresh_codec_executions, 2);
    }

    #[test]
    fn declaration_order_ties_and_parallel_results_are_stable() {
        // For this short payload both gzip levels produce the same byte count.
        // More recipes than workers cover worker reuse across ordered windows.
        let recipes = vec![gzip(9), gzip(1), gzip(6), gzip(7), gzip(8), gzip(9)];
        let mut serial = objective(recipes.clone(), 1, CacheBudget::disabled());
        let mut parallel = objective(recipes, 2, CacheBudget::disabled());
        let one = serial.evaluate("sample", b"tiny", "fixture bytes").unwrap();
        let two = parallel
            .evaluate("sample", b"tiny", "fixture bytes")
            .unwrap();
        assert_eq!(one.data, two.data);
        assert_eq!(one.records, two.records);
        assert_eq!(one.best["recipe"]["level"], 9);
        assert_eq!(one.coverage["initial_recipes"], 5);
        assert_eq!(serial.stats().codec_cache_entries, 0);
        assert_eq!(parallel.stats().codec_cache_bytes, 0);
    }

    #[test]
    fn parallel_failures_report_first_declared_error_and_never_cache_failure() {
        let mut first_bad = Recipe::new("alone");
        first_bad.preset = Some(u32::MAX);
        let mut later_bad = Recipe::new("xz");
        later_bad.lc = Some(5);
        for jobs in [1, 2, 4] {
            let mut cost = objective(
                vec![gzip(9), first_bad.clone(), gzip(1), later_bad.clone()],
                jobs,
                CacheBudget::default(),
            );
            for _ in 0..2 {
                let error = cost.measure(&[b'x'; 65537]).unwrap_err().to_string();
                assert!(error.contains("invalid LZMA preset"), "{jobs}: {error}");
            }
            assert_eq!(cost.stats().codec_not_started, 0);
            // Serial stops at the first failure; a parallel bounded window
            // observes both failures and preserves any successful siblings.
            assert_eq!(cost.stats().codec_failures, if jobs == 1 { 2 } else { 4 });
            assert_eq!(
                cost.stats().codec_cache_entries,
                if jobs == 1 { 1 } else { 2 }
            );
        }
    }

    #[test]
    fn legacy_submitted_seed_cannot_displace_previous_refinements() {
        let base = CodecPortfolio::legacy(false, None).plan(351);
        let mut submitted = Recipe::new("xz");
        submitted.preset = Some(1);
        let policy = CodecPortfolio::legacy(false, Some(submitted));
        let plan = policy.plan(351);
        let mut sizes = vec![100; base.initial.len()];
        sizes.push(1); // New xz seed displaces a legacy family if union is absent.
        let legacy_records: Vec<_> = base
            .initial
            .into_iter()
            .map(|recipe| (recipe, 100))
            .collect();
        let expected = codec::refinements(&legacy_records, false);
        let actual = policy.refinement_recipes(&plan, &sizes).unwrap();
        assert!(expected.iter().all(|recipe| actual.contains(recipe)));
        assert!(!policy.context()["exhaustive_declared_recipe_domain"]
            .as_bool()
            .unwrap());
    }
}
