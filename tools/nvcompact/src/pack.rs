//! Complete native packing candidates for the general 4k script category.
//! The packer itself is Rust. The explicitly declared submission loader uses
//! the permitted Python interpreter; it is never an ELF-only submission.
use crate::codec::{self, Recipe};
use anyhow::{bail, ensure, Result};
use serde::Serialize;

#[derive(Clone, Debug, Serialize)]
pub struct Packed {
    pub id: String,
    #[serde(skip)]
    pub data: Vec<u8>,
    pub payload_bytes: usize,
    pub loader_bytes: usize,
    pub payload_offset: usize,
    pub requirements: Vec<String>,
    pub runtime_profile: String,
    pub roundtrip_verified: bool,
    pub codec: Recipe,
}

fn x86_64(target: &str) -> bool {
    let target = target.to_ascii_lowercase().replace("amd64", "x86_64");
    target.contains("linux") && target.contains("x86_64")
}

pub fn candidate_ids(target: &str, codecs: Option<&[String]>) -> Result<Vec<String>> {
    ensure!(
        target.to_ascii_lowercase().contains("linux"),
        "packing requires declared Linux target"
    );
    let default = vec![
        "gzip".into(),
        "zlib".into(),
        "bzip2".into(),
        "xz".into(),
        "lzma".into(),
    ];
    let mut requests = codecs.unwrap_or(&default).to_vec();
    if codecs.is_none() && x86_64(target) {
        requests.push("xz-bcj".into());
    }
    let mut output = vec!["raw".to_string()];
    for request in requests {
        let expanded: Vec<String> = match request.as_str() {
            "raw" => vec![request],
            "gzip" | "zlib" | "bzip2" => [1, 9]
                .into_iter()
                .map(|level| format!("{request}-{level}"))
                .collect(),
            "xz" | "xz-bcj" | "lzma" => [0, 6, 9]
                .into_iter()
                .map(|level| format!("{request}-{level}"))
                .collect(),
            _ => {
                let (family, level) = request
                    .rsplit_once('-')
                    .ok_or_else(|| anyhow::anyhow!("unknown codec {request}"))?;
                let valid = match family {
                    "gzip" | "zlib" | "bzip2" => matches!(level, "1" | "9"),
                    "xz" | "xz-bcj" | "lzma" => matches!(level, "0" | "6" | "9"),
                    _ => false,
                };
                ensure!(valid, "unknown exact packing recipe {request}");
                vec![request]
            }
        };
        for item in expanded {
            ensure!(
                !item.starts_with("xz-bcj-") || x86_64(target),
                "x86 BCJ requires declared x86_64 Linux target"
            );
            if !output.contains(&item) {
                output.push(item);
            }
        }
    }
    Ok(output)
}

fn native_recipe(id: &str, input_size: usize) -> Result<(Recipe, &'static str)> {
    let (family, level) = id
        .rsplit_once('-')
        .ok_or_else(|| anyhow::anyhow!("expected exact packing recipe"))?;
    let level: u32 = level.parse()?;
    let (format, module) = match family {
        "gzip" => ("gzip", "gzip"),
        "zlib" => ("zlib", "zlib"),
        "bzip2" => ("bzip2", "bz2"),
        "xz" | "xz-bcj" => ("xz", "lzma"),
        "lzma" => ("alone", "lzma"),
        _ => bail!("unknown native codec {family}"),
    };
    let mut recipe = Recipe::new(format);
    if module == "lzma" {
        recipe.preset = Some(level);
        recipe.x86 = family == "xz-bcj";
        let cap = match level {
            0 => 1 << 18,
            6 => 1 << 23,
            9 => 1 << 26,
            _ => bail!("unsupported LZMA level"),
        };
        recipe.dict_size = Some(codec::dictionary_size(input_size, cap));
        if format == "xz" {
            recipe.check = Some("crc32".into());
        }
    } else {
        recipe.level = Some(level);
    }
    Ok((recipe, module))
}

/// Fixed-point loader offset: both the decimal offset and its digits count.
/// The narrow deployment contract is documented in the generated metadata.
pub fn loader(module: &str, offset: usize) -> Result<Vec<u8>> {
    ensure!(
        matches!(module, "gzip" | "zlib" | "bz2" | "lzma"),
        "unsupported loader module"
    );
    let python=format!(
        "import os,sys,signal,{module}\n\
         a=sys.argv;m=int(a[1],16);e=os.environ;k=\"LC_CTYPE\"\n\
         if a[2]:e[k]=a[3]\n\
         else:e.pop(k,None)\n\
         a=a[4:]\n\
         with open(a[0],\"rb\") as p:p.seek({offset});d={module}.decompress(p.read())\n\
         f=os.memfd_create(\"\",os.MFD_CLOEXEC)\n\
         with os.fdopen(f,\"wb\",closefd=False) as w:w.write(d)\n\
         os.fchmod(f,0o500)\n\
         for s in (signal.SIGPIPE,signal.SIGXFSZ):signal.signal(s,signal.SIG_IGN if m>>(s-1)&1 else signal.SIG_DFL)\n\
         os.execve(f,a,e)");
    ensure!(
        !python.contains('\''),
        "internal loader shell quoting error"
    );
    Ok(format!("#!/bin/sh\nexec python3 -I -S -c '{python}' \"$(while read k v;do [ \"$k\" = SigIgn: ]&&{{ printf %s \"$v\";break;}};done</proc/self/status)\" \"${{LC_CTYPE+x}}\" \"${{LC_CTYPE-}}\" \"$0\" \"$@\"\nexit 127\n").into_bytes())
}

fn wrap(payload: &[u8], module: &str) -> Result<(Vec<u8>, usize)> {
    let mut offset = 0;
    for _ in 0..16 {
        let header = loader(module, offset)?;
        let actual = header.len();
        if actual == offset {
            let mut data = header;
            data.extend_from_slice(payload);
            return Ok((data, offset));
        }
        ensure!(actual >= offset, "non-monotone native loader offset");
        offset = actual;
    }
    bail!("native loader offset did not converge")
}

pub fn pack_by_id(raw: &[u8], target: &str, id: &str) -> Result<Packed> {
    crate::elf::validate_executable(raw, target)?;
    let expanded = candidate_ids(target, Some(&[id.to_string()]))?;
    ensure!(
        expanded.iter().any(|value| value == id),
        "pack_by_id requires exact recipe ID"
    );
    if id == "raw" {
        return Ok(Packed {
            id: id.into(),
            data: raw.to_vec(),
            payload_bytes: raw.len(),
            loader_bytes: 0,
            payload_offset: 0,
            requirements: vec!["declared Linux ELF ABI".into()],
            runtime_profile: "native-elf".into(),
            roundtrip_verified: true,
            codec: Recipe::new("identity"),
        });
    }
    let (recipe, module) = native_recipe(id, raw.len())?;
    let payload = codec::compress(raw, &recipe)?;
    ensure!(
        codec::decode(&payload, &recipe, raw.len())? == raw,
        "native codec roundtrip failed"
    );
    let (data, offset) = wrap(&payload, module)?;
    ensure!(
        codec::decode(&data[offset..], &recipe, raw.len())? == raw,
        "embedded native payload roundtrip failed"
    );
    Ok(Packed {
        id: id.into(),
        data,
        payload_bytes: payload.len(),
        loader_bytes: offset,
        payload_offset: offset,
        requirements: vec![
            "/bin/sh with POSIX builtins".into(),
            "python3 >= 3.8".into(),
            format!("Python standard library {module}"),
            "/proc/self/status".into(),
            "Linux memfd_create and fd exec permitted".into(),
            "declared Linux ELF ABI".into(),
            "argv[1:], binary stdio, exit and inherited SIGPIPE/SIGXFSZ dispositions preserved"
                .into(),
            "no custom execve argv[0], self-file/exe observation or $ORIGIN-relative libraries"
                .into(),
        ],
        runtime_profile: "linux-script-python-memfd".into(),
        roundtrip_verified: true,
        codec: recipe,
    })
}

pub fn pack_variants(raw: &[u8], target: &str, codecs: Option<&[String]>) -> Result<Vec<Packed>> {
    candidate_ids(target, codecs)?
        .iter()
        .map(|id| pack_by_id(raw, target, id))
        .collect()
}
