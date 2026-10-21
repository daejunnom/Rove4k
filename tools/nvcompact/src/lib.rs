pub mod cflow;
pub mod codec;
pub mod csource;
pub mod elf;
pub mod envelope;
pub mod native;
pub mod notation;
pub mod pack;
pub mod process;
pub mod resource;
pub mod source_payload;
pub mod source_search;
pub mod uci;

pub fn sha256(bytes: &[u8]) -> String {
    use sha2::{Digest, Sha256};
    hex::encode(Sha256::digest(bytes))
}

pub fn write_json(path: &std::path::Path, value: &impl serde::Serialize) -> anyhow::Result<()> {
    use std::io::Write;
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let mut out = std::fs::File::create(path)?;
    serde_json::to_writer_pretty(&mut out, value)?;
    out.write_all(b"\n")?;
    Ok(())
}
