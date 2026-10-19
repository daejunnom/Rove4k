//! Deterministic, bounded codec recipes. The original stream is a separate
//! candidate: a finite search is never assumed to rediscover upstream settings.
use anyhow::{bail, ensure, Context, Result};
use serde::{Deserialize, Serialize};
use std::io::{Cursor, Read, Write};

pub const MAX_PAYLOAD: usize = 8 << 20;
const DECODER_MEMORY: u64 = 256 << 20;

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
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

fn read_bounded(reader: &mut impl Read, maximum: usize) -> Result<Vec<u8>> {
    let mut output = Vec::new();
    reader
        .take(maximum.checked_add(1).context("output bound overflow")? as u64)
        .read_to_end(&mut output)?;
    ensure!(
        output.len() <= maximum,
        "decompressed payload exceeds {maximum} bytes"
    );
    Ok(output)
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

fn lzma(data: &[u8], recipe: &Recipe, encode: bool, maximum: usize) -> Result<Vec<u8>> {
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
    let mut output = Vec::new();
    loop {
        let mut buffer = [0u8; 65536];
        stream.0.next_out = buffer.as_mut_ptr();
        stream.0.avail_out = buffer.len().min(maximum + 1 - output.len());
        let capacity = stream.0.avail_out;
        let before = stream.0.avail_in;
        let status = unsafe { lzma_sys::lzma_code(&mut stream.0, lzma_sys::LZMA_FINISH) };
        let written = capacity - stream.0.avail_out;
        output.extend_from_slice(&buffer[..written]);
        ensure!(
            output.len() <= maximum,
            "codec output exceeds {maximum} bytes"
        );
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

pub fn decode(data: &[u8], recipe: &Recipe, maximum: usize) -> Result<Vec<u8>> {
    match recipe.format.as_str() {
        "identity" => {
            ensure!(data.len() <= maximum, "identity exceeds payload bound");
            Ok(data.to_vec())
        }
        "gzip" => {
            let mut reader = flate2::bufread::GzDecoder::new(Cursor::new(data));
            let output = read_bounded(&mut reader, maximum)?;
            ensure!(
                reader.into_inner().position() == data.len() as u64,
                "trailing gzip data is unsupported"
            );
            Ok(output)
        }
        "zlib" => {
            let mut reader = flate2::bufread::ZlibDecoder::new(Cursor::new(data));
            let output = read_bounded(&mut reader, maximum)?;
            ensure!(
                reader.total_in() == data.len() as u64,
                "trailing zlib data is unsupported"
            );
            Ok(output)
        }
        "bzip2" => {
            let mut reader = bzip2::bufread::BzDecoder::new(Cursor::new(data));
            let output = read_bounded(&mut reader, maximum)?;
            ensure!(
                reader.total_in() == data.len() as u64,
                "trailing bzip2 data is unsupported"
            );
            Ok(output)
        }
        "alone" | "xz" | "raw" => lzma(data, recipe, false, maximum),
        other => bail!("unsupported decoder {other}"),
    }
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
