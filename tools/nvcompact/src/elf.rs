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
    Ok(output)
}
