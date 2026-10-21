//! Deterministic, bounded codec recipes. The original stream is a separate
//! candidate: a finite search is never assumed to rediscover upstream settings.
use anyhow::{bail, ensure, Result};
use serde::{Deserialize, Serialize};
use std::io::{Cursor, Read, Write};

pub const MAX_PAYLOAD: usize = 8 << 20;
const DECODER_MEMORY: u64 = 256 << 20;

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct Recipe {
    pub format: String,
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub x86: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub preset: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub level: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub dict_size: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub lc: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub lp: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub pb: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub mf: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub nice_len: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub depth: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub check: Option<String>,
}

impl Recipe {
    pub fn new(format: &str) -> Self {
        Self {
            format: format.into(),
            x86: false,
            preset: None,
            level: None,
            dict_size: None,
            lc: None,
            lp: None,
            pb: None,
            mf: None,
            nice_len: None,
            depth: None,
            check: None,
        }
    }
}

pub fn library_versions() -> serde_json::Value {
    // SAFETY: liblzma exposes a permanent, NUL-terminated version string.
    let lzma = unsafe { std::ffi::CStr::from_ptr(lzma_sys::lzma_version_string()) }
        .to_string_lossy()
        .into_owned();
    serde_json::json!({"lzma": lzma, "gzip_mtime":0, "gzip_os":255,
        "implementation":"Rust with liblzma, zlib and libbz2; Cargo.lock pins bindings"})
}

pub fn dictionary_size(length: usize, cap: u32) -> u32 {
    length
        .max(1)
        .checked_next_power_of_two()
        .unwrap_or(usize::MAX)
        .clamp(4096, cap as usize) as u32
}

/// Original context portfolio, followed by a measured match-finder refinement.
pub fn recipes(payload_size: usize, thorough: bool) -> Vec<Recipe> {
    let mut output = Vec::new();
    let dictionary = dictionary_size(payload_size, 8 << 20);
    for (format, x86) in [
        ("alone", false),
        ("xz", false),
        ("raw", false),
        ("raw", true),
    ] {
        for preset in [6, 9 | lzma_sys::LZMA_PRESET_EXTREME] {
            for lp in 0..=if thorough { 4 } else { 1 } {
                for lc in 0..=4 - lp {
                    for pb in 0..=if thorough { 4 } else { 2 } {
                        let mut recipe = Recipe::new(format);
                        recipe.x86 = x86;
                        recipe.preset = Some(preset);
                        recipe.dict_size = Some(dictionary);
                        recipe.lc = Some(lc);
                        recipe.lp = Some(lp);
                        recipe.pb = Some(pb);
                        output.push(recipe);
                    }
                }
            }
        }
    }
    for format in ["gzip", "bzip2"] {
        for level in [1, 9] {
            let mut recipe = Recipe::new(format);
            recipe.level = Some(level);
            output.push(recipe);
        }
    }
    output
}

pub fn refinements(records: &[(Recipe, usize)], thorough: bool) -> Vec<Recipe> {
    let mut ordered: Vec<_> = records.iter().enumerate().collect();
    ordered.sort_by_key(|(index, (_, size))| (*size, *index));
    let mut seeds: Vec<Recipe> = Vec::new();
    for (_, (recipe, _)) in ordered {
        if !matches!(recipe.format.as_str(), "alone" | "xz" | "raw") {
            continue;
        }
        if seeds
            .iter()
            .any(|item| item.format == recipe.format && item.x86 == recipe.x86)
        {
            continue;
        }
        seeds.push(recipe.clone());
        if seeds.len() == 2 {
            break;
        }
    }
    let nice: Vec<u32> = if thorough {
        (4..=273).collect()
    } else {
        vec![4, 8, 16, 24, 32, 48, 64, 96, 128, 192, 273]
    };
    let mut output = Vec::new();
    for seed in seeds {
        for mf in [
            lzma_sys::LZMA_MF_HC3,
            lzma_sys::LZMA_MF_HC4,
            lzma_sys::LZMA_MF_BT2,
            lzma_sys::LZMA_MF_BT3,
            lzma_sys::LZMA_MF_BT4,
        ] {
            for length in &nice {
                let mut recipe = seed.clone();
                recipe.mf = Some(mf as u32);
                recipe.nice_len = Some(*length);
                output.push(recipe);
            }
        }
    }
    output
}

/// Whether measured initial costs choose a second, adaptive recipe set.
/// `None` evaluates the declared initial set completely; `LegacyUnion` is a
/// heuristic and never promises to enumerate every match-finder combination.
#[derive(Clone, Copy, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum RefinementMode {
    None,
    LegacyUnion,
}

#[derive(Clone, Debug, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
enum PortfolioRecipes {
    Legacy {
        thorough: bool,
        submitted: Option<Recipe>,
    },
    Fixed {
        recipes: Vec<Recipe>,
        declared_count: usize,
    },
}

/// Owns one finite codec policy, independently of payload generation and
/// compression. In particular an added submitted recipe cannot displace a
/// refinement that the earlier legacy search would have measured.
#[derive(Clone, Debug, Serialize)]
pub struct CodecPortfolio {
    recipes: PortfolioRecipes,
    refinement_mode: RefinementMode,
}

#[derive(Clone, Debug)]
pub struct PortfolioPlan {
    pub initial: Vec<Recipe>,
    legacy_initial_count: usize,
}

impl CodecPortfolio {
    pub fn legacy(thorough: bool, submitted: Option<Recipe>) -> Self {
        Self {
            recipes: PortfolioRecipes::Legacy {
                thorough,
                submitted,
            },
            refinement_mode: RefinementMode::LegacyUnion,
        }
    }

    /// Preserve declaration order while coalescing exactly identical recipes.
    /// This declares the complete codec domain, suitable for a finite source ×
    /// codec comparison without source-dependent refinement seed selection.
    pub fn fixed(recipes: Vec<Recipe>) -> Result<Self> {
        ensure!(
            (1..=16_384).contains(&recipes.len()),
            "fixed codec portfolio must contain 1..16384 recipes"
        );
        let declared_count = recipes.len();
        let mut seen = std::collections::HashSet::new();
        let recipes = recipes
            .into_iter()
            .filter(|recipe| seen.insert(recipe.clone()))
            .collect();
        Ok(Self {
            recipes: PortfolioRecipes::Fixed {
                recipes,
                declared_count,
            },
            refinement_mode: RefinementMode::None,
        })
    }

    pub fn with_refinement_mode(mut self, mode: RefinementMode) -> Self {
        self.refinement_mode = mode;
        self
    }

    pub fn plan(&self, payload_size: usize) -> PortfolioPlan {
        match &self.recipes {
            PortfolioRecipes::Legacy {
                thorough,
                submitted,
            } => {
                let mut initial = recipes(payload_size, *thorough);
                let legacy_initial_count = initial.len();
                if let Some(recipe) = submitted {
                    if !initial.contains(recipe) {
                        initial.push(recipe.clone());
                    }
                }
                PortfolioPlan {
                    initial,
                    legacy_initial_count,
                }
            }
            PortfolioRecipes::Fixed { recipes, .. } => PortfolioPlan {
                initial: recipes.clone(),
                legacy_initial_count: recipes.len(),
            },
        }
    }

    pub fn refinement_recipes(
        &self,
        plan: &PortfolioPlan,
        complete_file_sizes: &[usize],
    ) -> Result<Vec<Recipe>> {
        ensure!(
            plan.initial.len() == complete_file_sizes.len(),
            "codec refinement costs do not match initial recipe domain"
        );
        ensure!(
            plan.legacy_initial_count <= plan.initial.len(),
            "legacy codec prefix exceeds initial domain"
        );
        if self.refinement_mode == RefinementMode::None {
            return Ok(Vec::new());
        }
        let thorough = matches!(
            self.recipes,
            PortfolioRecipes::Legacy { thorough: true, .. }
        );
        let sizes: Vec<_> = plan
            .initial
            .iter()
            .cloned()
            .zip(complete_file_sizes.iter().copied())
            .collect();
        let mut output = refinements(&sizes[..plan.legacy_initial_count], thorough);
        for recipe in refinements(&sizes, thorough) {
            if !output.contains(&recipe) {
                output.push(recipe);
            }
        }
        Ok(output)
    }

    pub fn context(&self) -> serde_json::Value {
        serde_json::json!({
            "policy":self,
            "domain":if self.refinement_mode == RefinementMode::None {
                "all declared initial recipes; exact duplicates retain the first occurrence"
            } else if matches!(&self.recipes, PortfolioRecipes::Fixed { .. }) {
                "declared initial recipes followed by measured two-family match-finder refinements"
            } else {
                "legacy initial recipes plus submitted recipe, then union of legacy and augmented two-family refinements"
            },
            "adaptive_refinement":self.refinement_mode != RefinementMode::None,
            "exhaustive_declared_recipe_domain":self.refinement_mode == RefinementMode::None,
            "global_optimum":false,
            "tie_order":"initial declaration order, followed by refinement declaration order"
        })
    }
}

/// Drain a decoder in bounded chunks. The extra byte distinguishes exact
/// output from a stream which only shares the expected prefix.
fn read_chunks(
    reader: &mut impl Read,
    maximum: usize,
    emit: &mut impl FnMut(&[u8]) -> Result<()>,
) -> Result<()> {
    ensure!(maximum < usize::MAX, "invalid output limit");
    let mut output_bytes = 0;
    let mut buffer = [0u8; 65536];
    loop {
        let capacity = buffer.len().min(maximum + 1 - output_bytes);
        let written = match reader.read(&mut buffer[..capacity]) {
            Err(error) if error.kind() == std::io::ErrorKind::Interrupted => continue,
            result => result?,
        };
        if written == 0 {
            return Ok(());
        }
        output_bytes += written;
        ensure!(
            output_bytes <= maximum,
            "decompressed payload exceeds {maximum} bytes"
        );
        emit(&buffer[..written])?;
    }
}

/// One raw liblzma stream, owned by its calling worker and always finalized.
struct LzmaStream(lzma_sys::lzma_stream);
impl Drop for LzmaStream {
    fn drop(&mut self) {
        // SAFETY: zero initialization is LZMA_STREAM_INIT; initialization and all
        // subsequent operations happen through this uniquely owned stream.
        unsafe { lzma_sys::lzma_end(&mut self.0) }
    }
}

fn lzma_chunks(
    data: &[u8],
    recipe: &Recipe,
    encode: bool,
    maximum: usize,
    emit: &mut impl FnMut(&[u8]) -> Result<()>,
) -> Result<()> {
    ensure!(maximum < usize::MAX, "invalid output limit");
    ensure!(
        !recipe.x86 || recipe.format != "alone",
        "LZMA-alone cannot contain BCJ"
    );
    // SAFETY: the C API explicitly specifies zero initialization for options
    // before lzma_lzma_preset and for LZMA_STREAM_INIT. Options, filters, input
    // and each output buffer remain alive and exclusively borrowed throughout
    // every call. No raw pointers escape this function or cross worker threads.
    let mut options: lzma_sys::lzma_options_lzma = unsafe { std::mem::zeroed() };
    let preset = recipe.preset.unwrap_or(6);
    ensure!(
        unsafe { lzma_sys::lzma_lzma_preset(&mut options, preset) } == 0,
        "invalid LZMA preset {preset}"
    );
    options.dict_size = recipe.dict_size.unwrap_or(8 << 20);
    ensure!(
        (4096..=64 << 20).contains(&options.dict_size),
        "LZMA dictionary exceeds bounded profile"
    );
    if let Some(v) = recipe.lc {
        options.lc = v;
    }
    if let Some(v) = recipe.lp {
        options.lp = v;
    }
    if let Some(v) = recipe.pb {
        options.pb = v;
    }
    if let Some(v) = recipe.mf {
        options.mf = v as lzma_sys::lzma_match_finder;
    }
    if let Some(v) = recipe.nice_len {
        options.nice_len = v;
    }
    if let Some(v) = recipe.depth {
        options.depth = v;
    }
    ensure!(
        options.lc <= 4 && options.lp <= 4 && options.lc + options.lp <= 4 && options.pb <= 4,
        "unsupported LZMA context parameters"
    );
    let filter = if recipe.format == "alone" {
        lzma_sys::LZMA_FILTER_LZMA1
    } else {
        lzma_sys::LZMA_FILTER_LZMA2
    };
    let mut filters = Vec::new();
    if recipe.x86 {
        filters.push(lzma_sys::lzma_filter {
            id: lzma_sys::LZMA_FILTER_X86,
            options: std::ptr::null_mut(),
        });
    }
    filters.push(lzma_sys::lzma_filter {
        id: filter,
        options: (&mut options as *mut lzma_sys::lzma_options_lzma).cast(),
    });
    filters.push(lzma_sys::lzma_filter {
        id: u64::MAX,
        options: std::ptr::null_mut(),
    });
    let mut stream = LzmaStream(unsafe { std::mem::zeroed() });
    let check = match recipe.check.as_deref().unwrap_or("none") {
        "none" => lzma_sys::LZMA_CHECK_NONE,
        "crc32" => lzma_sys::LZMA_CHECK_CRC32,
        "crc64" => lzma_sys::LZMA_CHECK_CRC64,
        other => bail!("unsupported integrity check {other}"),
    };
    let init = unsafe {
        match (encode, recipe.format.as_str()) {
            (true, "alone") => lzma_sys::lzma_alone_encoder(&mut stream.0, &options),
            (true, "xz") => lzma_sys::lzma_stream_encoder(&mut stream.0, filters.as_ptr(), check),
            (true, "raw") => lzma_sys::lzma_raw_encoder(&mut stream.0, filters.as_ptr()),
            (false, "alone") => lzma_sys::lzma_alone_decoder(&mut stream.0, DECODER_MEMORY),
            (false, "xz") => lzma_sys::lzma_stream_decoder(&mut stream.0, DECODER_MEMORY, 0),
            (false, "raw") => lzma_sys::lzma_raw_decoder(&mut stream.0, filters.as_ptr()),
            _ => bail!("unsupported LZMA format {}", recipe.format),
        }
    };
    ensure!(
        init == lzma_sys::LZMA_OK,
        "liblzma initialization failed: {init}"
    );
    stream.0.next_in = data.as_ptr();
    stream.0.avail_in = data.len();
    let mut output_bytes = 0;
    let mut buffer = [0u8; 65536];
    loop {
        stream.0.next_out = buffer.as_mut_ptr();
        stream.0.avail_out = buffer.len().min(maximum + 1 - output_bytes);
        let capacity = stream.0.avail_out;
        let before = stream.0.avail_in;
        let status = unsafe { lzma_sys::lzma_code(&mut stream.0, lzma_sys::LZMA_FINISH) };
        let written = capacity - stream.0.avail_out;
        output_bytes += written;
        ensure!(
            output_bytes <= maximum,
            "codec output exceeds {maximum} bytes"
        );
        emit(&buffer[..written])?;
        if status == lzma_sys::LZMA_STREAM_END {
            ensure!(
                stream.0.avail_in == 0,
                "trailing compressed data is unsupported"
            );
            break;
        }
        ensure!(
            status == lzma_sys::LZMA_OK,
            "liblzma stream failed: {status}"
        );
        ensure!(
            written > 0 || stream.0.avail_in < before,
            "unfinished LZMA stream made no progress"
        );
    }
    Ok(())
}

fn lzma(data: &[u8], recipe: &Recipe, encode: bool, maximum: usize) -> Result<Vec<u8>> {
    let mut output = Vec::new();
    lzma_chunks(data, recipe, encode, maximum, &mut |chunk| {
        output.extend_from_slice(chunk);
        Ok(())
    })?;
    Ok(output)
}

pub fn compress(data: &[u8], recipe: &Recipe) -> Result<Vec<u8>> {
    ensure!(
        data.len() <= 64 << 20,
        "compression input exceeds 64 MiB profile"
    );
    let level = recipe.level.unwrap_or(9);
    ensure!((1..=9).contains(&level), "compression level must be 1..9");
    match recipe.format.as_str() {
        "identity" => Ok(data.to_vec()),
        "gzip" => {
            let mut writer = flate2::GzBuilder::new()
                .mtime(0)
                .operating_system(255)
                .write(Vec::new(), flate2::Compression::new(level));
            writer.write_all(data)?;
            Ok(writer.finish()?)
        }
        "zlib" => {
            let mut writer =
                flate2::write::ZlibEncoder::new(Vec::new(), flate2::Compression::new(level));
            writer.write_all(data)?;
            Ok(writer.finish()?)
        }
        "bzip2" => {
            let mut writer =
                bzip2::write::BzEncoder::new(Vec::new(), bzip2::Compression::new(level));
            writer.write_all(data)?;
            Ok(writer.finish()?)
        }
        "alone" | "xz" | "raw" => lzma(
            data,
            recipe,
            true,
            data.len().saturating_mul(2).saturating_add(65536),
        ),
        other => bail!("unsupported codec {other}"),
    }
}

fn decode_chunks(
    data: &[u8],
    recipe: &Recipe,
    maximum: usize,
    emit: &mut impl FnMut(&[u8]) -> Result<()>,
) -> Result<()> {
    match recipe.format.as_str() {
        "identity" => {
            ensure!(data.len() <= maximum, "identity exceeds payload bound");
            emit(data)
        }
        "gzip" => {
            let mut reader = flate2::bufread::GzDecoder::new(Cursor::new(data));
            read_chunks(&mut reader, maximum, emit)?;
            ensure!(
                reader.into_inner().position() == data.len() as u64,
                "trailing gzip data is unsupported"
            );
            Ok(())
        }
        "zlib" => {
            let mut reader = flate2::bufread::ZlibDecoder::new(Cursor::new(data));
            read_chunks(&mut reader, maximum, emit)?;
            ensure!(
                reader.total_in() == data.len() as u64,
                "trailing zlib data is unsupported"
            );
            Ok(())
        }
        "bzip2" => {
            let mut reader = bzip2::bufread::BzDecoder::new(Cursor::new(data));
            read_chunks(&mut reader, maximum, emit)?;
            ensure!(
                reader.total_in() == data.len() as u64,
                "trailing bzip2 data is unsupported"
            );
            Ok(())
        }
        "alone" | "xz" | "raw" => lzma_chunks(data, recipe, false, maximum, emit),
        other => bail!("unsupported decoder {other}"),
    }
}

pub fn decode(data: &[u8], recipe: &Recipe, maximum: usize) -> Result<Vec<u8>> {
    let mut output = Vec::new();
    decode_chunks(data, recipe, maximum, &mut |chunk| {
        output.extend_from_slice(chunk);
        Ok(())
    })?;
    Ok(output)
}

/// Verify every restored byte and the exact stream boundary without retaining
/// another full decoded payload. Decoder integrity/trailing-input checks are
/// shared with `decode`; a matching prefix is never accepted as a roundtrip.
pub fn verify_decode(data: &[u8], recipe: &Recipe, expected: &[u8]) -> Result<()> {
    let mut offset = 0;
    decode_chunks(data, recipe, expected.len(), &mut |chunk| {
        let end = offset + chunk.len();
        ensure!(
            expected.get(offset..end) == Some(chunk),
            "codec roundtrip changed payload"
        );
        offset = end;
        Ok(())
    })?;
    ensure!(
        offset == expected.len(),
        "codec roundtrip truncated payload"
    );
    Ok(())
}

pub fn decoder_for(recipe: &Recipe) -> Result<String> {
    Ok(match recipe.format.as_str() {
        "alone" | "xz" => "xz -d".into(),
        "raw" => format!(
            "xz -dcFraw {}--lzma2",
            if recipe.x86 { "--x86 " } else { "" }
        ),
        "gzip" => "gzip -d".into(),
        "bzip2" => "bzip2 -d".into(),
        other => bail!("no allowed shell decoder for {other}"),
    })
}

#[cfg(test)]
mod streaming_tests {
    use super::*;

    #[test]
    fn streamed_comparison_checks_every_byte_length_and_stream_end() {
        let payload: Vec<_> = (0..200_003).map(|i| (i % 251) as u8).collect();
        for format in ["identity", "gzip", "zlib", "bzip2", "alone", "xz", "raw"] {
            let mut recipe = Recipe::new(format);
            recipe.dict_size = Some(1 << 18);
            let packed = compress(&payload, &recipe).unwrap();
            assert_eq!(decode(&packed, &recipe, payload.len()).unwrap(), payload);
            verify_decode(&packed, &recipe, &payload).unwrap();
            let mut different = payload.clone();
            different[65_537] ^= 1;
            assert!(
                verify_decode(&packed, &recipe, &different).is_err(),
                "{format}"
            );
            assert!(
                verify_decode(&packed, &recipe, &payload[..payload.len() - 1]).is_err(),
                "{format}"
            );
            let mut longer = payload.clone();
            longer.push(0);
            assert!(
                verify_decode(&packed, &recipe, &longer).is_err(),
                "{format}"
            );
            let mut trailing = packed.clone();
            trailing.push(0);
            assert!(
                verify_decode(&trailing, &recipe, &payload).is_err(),
                "{format}"
            );
            assert!(
                verify_decode(&packed[..packed.len() - 1], &recipe, &payload).is_err(),
                "{format}"
            );
            let empty = compress(&[], &recipe).unwrap();
            verify_decode(&empty, &recipe, &[]).unwrap();
        }
    }
}
