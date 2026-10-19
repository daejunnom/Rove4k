//! Restricted ELF metadata removal. Identity remains available for golfed ELF
//! files, which may execute normally-unused header bytes as code or data.
use anyhow::{ensure, Context, Result};

#[derive(Clone, Debug)]
pub struct Deployment {
    pub id: String,
    pub data: Vec<u8>,
    pub preconditions: Vec<String>,
}
fn u16le(data: &[u8], offset: usize) -> u16 {
    u16::from_le_bytes(data[offset..offset + 2].try_into().unwrap())
}
fn u32le(data: &[u8], offset: usize) -> u32 {
    u32::from_le_bytes(data[offset..offset + 4].try_into().unwrap())
}
fn u64le(data: &[u8], offset: usize) -> u64 {
    u64::from_le_bytes(data[offset..offset + 8].try_into().unwrap())
}
fn end(offset: u64, size: u64, total: usize, label: &str) -> Result<usize> {
    let result = offset
        .checked_add(size)
        .with_context(|| format!("{label} extent overflow"))?;
    ensure!(result <= total as u64, "{label} extends beyond the input");
    Ok(result as usize)
}

pub fn validate_executable(data: &[u8], target: &str) -> Result<()> {
    ensure!(
        target.to_ascii_lowercase().contains("linux"),
        "native packing requires declared Linux target"
    );
    ensure!(
        data.len() >= 52 && data.starts_with(b"\x7fELF"),
        "native packing requires an ELF executable"
    );
    ensure!(
        matches!(data[4], 1 | 2) && matches!(data[5], 1 | 2) && data[6] == 1,
        "unsupported ELF identification"
    );
    ensure!(data[4] != 2 || data.len() >= 64, "truncated ELF64 header");
    let kind = if data[5] == 1 {
        u16le(data, 16)
    } else {
        u16::from_be_bytes(data[16..18].try_into().unwrap())
    };
    ensure!(matches!(kind, 2 | 3), "ELF is not ET_EXEC or ET_DYN");
    let normalized = target.to_ascii_lowercase().replace("amd64", "x86_64");
    if normalized.contains("x86_64") {
        ensure!(
            data[4] == 2 && data[5] == 1 && u16le(data, 18) == 62,
            "declared x86_64 target conflicts with ELF header"
        );
    }
    Ok(())
}

pub fn sectionless(data: &[u8]) -> Result<Vec<u8>> {
    ensure!(data.len() >= 64, "truncated ELF64 header");
    validate_executable(data, "x86_64-unknown-linux-gnu")?;
    ensure!(
        matches!(data[7], 0 | 3) && data[8] == 0,
        "requires System V/Linux ABI version zero"
    );
    ensure!(
        u32le(data, 20) == 1 && u32le(data, 48) == 0,
        "requires ordinary x86-64 ELF flags and version"
    );
    let phoff = u64le(data, 32);
    let shoff = u64le(data, 40);
    let ehsize = u16le(data, 52);
    let phentsize = u16le(data, 54);
    let phnum = u16le(data, 56);
    let shentsize = u16le(data, 58);
    let shnum = u16le(data, 60);
    let shstrndx = u16le(data, 62);
    ensure!(
        ehsize == 64 && phentsize == 56,
        "unexpected ELF/program-header size"
    );
    ensure!(
        phnum > 0 && phnum < 0xffff && phoff >= 64,
        "extended numbering or overlapping program headers"
    );
    let phend = end(phoff, phnum as u64 * 56, data.len(), "program headers")?;
    if shoff == 0 {
        ensure!(
            shnum == 0 && shstrndx == 0 && matches!(shentsize, 0 | 64),
            "inconsistent absent section table"
        );
    } else {
        ensure!(
            shoff >= 64 && shentsize == 64,
            "unsupported section header layout"
        );
        ensure!(
            shnum > 0 && shnum < 0xff00 && shstrndx < shnum,
            "unsupported section numbering"
        );
        end(shoff, shnum as u64 * 64, data.len(), "section headers")?;
        for index in 0..shnum {
            let base = shoff as usize + index as usize * 64;
            let kind = u32le(data, base + 4);
            let size = u64le(data, base + 32);
            let link = u32le(data, base + 40);
            let info = u32le(data, base + 44);
            if index == 0 {
                ensure!(
                    kind == 0 && size == 0 && link == 0 && info == 0,
                    "nonordinary section zero"
                );
            } else if !matches!(kind, 0 | 8) {
                end(u64le(data, base + 24), size, data.len(), "section payload")?;
            }
        }
    }
    let mut keep = 64.max(phend);
    let mut loads = 0;
    for index in 0..phnum {
        let base = phoff as usize + index as usize * 56;
        let kind = u32le(data, base);
        let offset = u64le(data, base + 8);
        let vaddr = u64le(data, base + 16);
        let filesz = u64le(data, base + 32);
        let memsz = u64le(data, base + 40);
        let align = u64le(data, base + 48);
        keep = keep.max(end(offset, filesz, data.len(), "program segment")?);
        vaddr
            .checked_add(memsz)
            .context("segment virtual extent overflow")?;
        if kind == 1 {
            loads += 1;
            ensure!(filesz <= memsz, "PT_LOAD file size exceeds memory size");
            ensure!(
                align <= 1 || align.is_power_of_two(),
                "PT_LOAD alignment is not a power of two"
            );
            ensure!(
                align <= 1 || offset % align == vaddr % align,
                "PT_LOAD file and virtual alignment differ"
            );
        }
    }
    ensure!(loads > 0, "ELF has no loadable segment");
    let mut result = data[..keep].to_vec();
    result[40..48].fill(0);
    result[58..64].fill(0);
    Ok(result)
}

pub fn deployment_variants(
    data: &[u8],
    allow_section_header_removal: bool,
) -> Result<Vec<Deployment>> {
    deployment_variants_with_options(data, allow_section_header_removal, false)
}

/// Replace a final writable segment's stored zero suffix with ELF zero-fill.
/// This deliberately supports only ordinary static x86-64 ET_EXEC layouts.
/// The caller must exclude observation of the file and its mapped ELF headers.
pub fn load_zero_tail(data: &[u8]) -> Result<Option<Vec<u8>>> {
    let mut result = sectionless(data)?;
    ensure!(u16le(&result, 16) == 2, "zero-tail requires static ET_EXEC");
    let phoff = u64le(&result, 32) as usize;
    let phnum = u16le(&result, 56) as usize;
    let floor = 64.max(phoff + phnum * 56);
    let mut last_load = None;
    let mut previous_page_end = 0u64;
    for index in 0..phnum {
        let base = phoff + index * 56;
        let kind = u32le(&result, base);
        let offset = u64le(&result, base + 8);
        let vaddr = u64le(&result, base + 16);
        let filesz = u64le(&result, base + 32);
        let memsz = u64le(&result, base + 40);
        ensure!(
            matches!(kind, 0 | 1 | 6 | 0x6474e551),
            "zero-tail requires no interpreter, dynamic linking, TLS, notes or other program segments"
        );
        if kind == 1 {
            ensure!(
                offset % 4096 == vaddr % 4096,
                "zero-tail requires Linux x86-64 page-congruent mappings"
            );
            let page_end = vaddr
                .checked_add(memsz)
                .and_then(|n| n.checked_add(4095))
                .context("zero-tail page extent overflow")?
                & !4095;
            ensure!(
                vaddr & !4095 >= previous_page_end,
                "zero-tail requires ordered PT_LOAD mappings without shared virtual pages"
            );
            previous_page_end = page_end;
            last_load = Some(base);
        } else if matches!(kind, 0 | 0x6474e551) {
            ensure!(
                filesz == 0,
                "zero-tail requires empty NULL/STACK file extents"
            );
        }
    }
    let base = last_load.context("zero-tail has no PT_LOAD")?;
    ensure!(
        u32le(&result, base + 4) == 6,
        "zero-tail requires a readable/writable, non-executable final PT_LOAD"
    );
    let offset = u64le(&result, base + 8) as usize;
    let filesz = u64le(&result, base + 32) as usize;
    ensure!(
        offset + filesz == result.len() && filesz > 0,
        "zero-tail requires the last PT_LOAD to end at the retained file end"
    );
    // Keep a nonempty initialized prefix and every header. Linux's zero-filesz
    // path has different mapping behavior, so it is intentionally not used.
    let earliest = floor.max(offset + 1);
    let mut keep = result.len();
    while keep > earliest && result[keep - 1] == 0 {
        keep -= 1;
    }
    if keep == result.len() {
        return Ok(None);
    }
    for index in 0..phnum {
        let other = phoff + index * 56;
        if other != base {
            ensure!(
                u64le(&result, other + 8) + u64le(&result, other + 32) <= keep as u64,
                "zero-tail suffix is also covered by another program segment"
            );
        }
    }
    result[base + 32..base + 40].copy_from_slice(&((keep - offset) as u64).to_le_bytes());
    result.truncate(keep);
    // Re-run the ordinary ELF extent checks on the emitted file. This validates
    // the representation, not the caller's runtime observation contract.
    ensure!(
        sectionless(&result)? == result,
        "zero-tail emitted inconsistent ELF"
    );
    Ok(Some(result))
}

pub fn deployment_variants_with_options(
    data: &[u8],
    allow_section_header_removal: bool,
    allow_load_zero_tail: bool,
) -> Result<Vec<Deployment>> {
    ensure!(
        !allow_load_zero_tail || allow_section_header_removal,
        "allow_load_zero_tail also requires allow_section_header_removal"
    );
    let mut output = vec![Deployment {
        id: "original".into(),
        data: data.to_vec(),
        preconditions: vec!["identity bytes".into()],
    }];
    if allow_section_header_removal {
        output.push(Deployment {
            id: "no-section-headers".into(),
            data: sectionless(data)?,
            preconditions: vec![
                "declared Linux ELF64LE x86-64 ordinary executable layout".into(),
                "self-file and section-header bytes are unobserved by runtime/deployment".into(),
                "edited metadata is not repurposed as executable code or data".into(),
                "ELF/program-header tables and all program-segment file extents retained".into(),
                "complete final artifact still requires actual execution verification".into(),
            ],
        });
    }
    if allow_load_zero_tail {
        if let Some(compact) = load_zero_tail(data)? {
            output.push(Deployment {
                id: "no-section-headers-zero-tail".into(),
                data: compact,
                preconditions: vec![
                    "explicit ordinary static Linux ELF64LE x86-64 ET_EXEC deployment".into(),
                    "final RW/non-X PT_LOAD; ordered 4096-byte pages without virtual overlap".into(),
                    "only trailing zero file bytes removed; p_memsz, addresses and permissions retained".into(),
                    "self-file, section/program headers and AT_PHDR contents are unobserved".into(),
                    "edited metadata is not repurposed as executable code or data".into(),
                    "no interpreter, dynamic linking, TLS, notes or unsupported program segments".into(),
                    "complete final artifact still requires actual execution verification".into(),
                ],
            });
        }
    }
    Ok(output)
}
