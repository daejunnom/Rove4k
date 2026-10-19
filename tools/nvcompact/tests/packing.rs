use nvcompact::{
    codec::{self, Recipe},
    elf, envelope, pack, process, sha256, write_json,
};
use serde_json::{json, Value};
use std::{fs, path::Path};

fn input() -> Vec<u8> {
    let mut data = b"NVCompact: exact input, bounded output.\0\n".repeat(7);
    data.extend(0u8..64);
    data
}

fn recipe(value: Value) -> Recipe {
    serde_json::from_value(value).unwrap()
}

#[test]
fn codec_outputs_match_independent_v03_compressor_vectors() {
    // These four vectors were generated from the 0.3 Python compressor before
    // migration, using its liblzma/libbz2 backends. No Python executes in tests.
    let sample = input();
    assert_eq!(sample.len(), 351);
    let cases = [
        (
            json!({"format":"alone","preset":2147483657u32,"dict_size":4096,"lc":0,"lp":0,"pb":2}),
            122,
            "383270609dc5ec56dd6385ca498ea89c3c515bd4fcf6dd71d76a5c60a934fec0",
        ),
        (
            json!({"format":"xz","preset":6,"dict_size":4096,"lc":3,"lp":0,"pb":2}),
            160,
            "00766b4cae9f3c57f210df3721e0186d1740ff5c7cc7ffd0e71c00a3de287059",
        ),
        (
            json!({"format":"raw","preset":2147483657u32,"dict_size":4096,"lc":0,"lp":1,"pb":0,"x86":true}),
            112,
            "bf882731cf8c5e5991b6aa3c69c229463f376299f8fb74e33eeb7651ee74c737",
        ),
        (
            json!({"format":"bzip2","level":9}),
            188,
            "4ad62bba434b5003788419a96b4177f2137950f1fe6b9e9cefabff7ab3fe95cf",
        ),
    ];
    for (value, size, digest) in cases {
        let recipe = recipe(value);
        let compressed = codec::compress(&sample, &recipe).unwrap();
        assert_eq!(compressed.len(), size);
        assert_eq!(sha256(&compressed), digest);
        assert_eq!(codec::decode(&compressed, &recipe, 1000).unwrap(), sample);
    }
}

#[test]
fn codec_rejects_truncation_trailing_bytes_and_output_expansion() {
    let sample = input();
    for format in ["gzip", "zlib", "bzip2", "alone", "xz", "raw"] {
        let recipe = Recipe::new(format);
        let blob = codec::compress(&sample, &recipe).unwrap();
        assert_eq!(codec::decode(&blob, &recipe, 1000).unwrap(), sample);
        assert!(
            codec::decode(&blob[..blob.len() - 1], &recipe, 1000).is_err(),
            "accepted truncated {format}"
        );
        let mut trailing = blob.clone();
        trailing.push(0);
        assert!(
            codec::decode(&trailing, &recipe, 1000).is_err(),
            "accepted trailing {format}"
        );
        assert!(
            codec::decode(&blob, &recipe, sample.len() - 1).is_err(),
            "ignored {format} output bound"
        );
    }
}

#[test]
fn portfolio_retains_original_context_and_matchfinder_search() {
    let recipes = codec::recipes(351, false);
    assert_eq!(recipes.len(), 220);
    let sizes: Vec<_> = recipes.iter().cloned().map(|r| (r, 100)).collect();
    let refined = codec::refinements(&sizes, false);
    assert_eq!(refined.len(), 110);
    assert!(recipes
        .iter()
        .any(|r| r.lc == Some(0) && r.lp == Some(1) && r.pb == Some(0) && r.x86));
    assert!(refined
        .iter()
        .any(|r| r.nice_len == Some(273) && r.mf == Some(lzma_sys::LZMA_MF_BT4 as u32)));
    assert_eq!(codec::recipes(351, true).len(), 604);
}

#[test]
fn native_loader_preserves_v03_complete_header_bytes() {
    for (module, length, digest) in [
        (
            "gzip",
            597,
            "5174a44bde7707d381846d50ad6a6a1c7102b285851fb92a49d90120012ea20c",
        ),
        (
            "zlib",
            597,
            "b4aec99c2e1841d16b7370e36f146b9f5847a81abc94b2e4dcd9fcf07597b687",
        ),
        (
            "bz2",
            595,
            "9f1665c1c7968d4854b4d0ad2ede1d2e0c13ce33fa8a38da6234fbfb920cd8fb",
        ),
        (
            "lzma",
            597,
            "c6338132c8b9cb981e894632e2f6c637fefbdfe4e5b6ecf579eb5600eb9882d1",
        ),
    ] {
        let header = pack::loader(module, 597).unwrap();
        assert_eq!(header.len(), length);
        assert_eq!(sha256(&header), digest);
    }
    assert!(pack::candidate_ids("aarch64-unknown-linux-gnu", Some(&["xz-bcj".into()])).is_err());
    assert!(pack::pack_by_id(b"bad", "x86_64-unknown-linux-gnu", "xz-6").is_err());
}

fn ordinary_elf() -> Vec<u8> {
    let mut data = vec![0u8; 272];
    data[..7].copy_from_slice(b"\x7fELF\x02\x01\x01");
    data[16..18].copy_from_slice(&2u16.to_le_bytes());
    data[18..20].copy_from_slice(&62u16.to_le_bytes());
    data[20..24].copy_from_slice(&1u32.to_le_bytes());
    data[24..32].copy_from_slice(&0x400080u64.to_le_bytes());
    data[32..40].copy_from_slice(&64u64.to_le_bytes());
    data[40..48].copy_from_slice(&144u64.to_le_bytes());
    for (offset, value) in [(52, 64u16), (54, 56), (56, 1), (58, 64), (60, 2), (62, 0)] {
        data[offset..offset + 2].copy_from_slice(&value.to_le_bytes());
    }
    data[64..68].copy_from_slice(&1u32.to_le_bytes());
    data[68..72].copy_from_slice(&5u32.to_le_bytes());
    data[80..88].copy_from_slice(&0x400000u64.to_le_bytes());
    data[96..104].copy_from_slice(&144u64.to_le_bytes());
    data[104..112].copy_from_slice(&160u64.to_le_bytes());
    data[112..120].copy_from_slice(&4096u64.to_le_bytes());
    data[128..144].fill(0x90);
    data[212..216].copy_from_slice(&1u32.to_le_bytes());
    data[232..240].copy_from_slice(&128u64.to_le_bytes());
    data[240..248].copy_from_slice(&16u64.to_le_bytes());
    data
}

#[test]
fn elf_identity_is_default_and_explicit_section_removal_retains_segments() {
    let original = ordinary_elf();
    let identity = elf::deployment_variants(&original, false).unwrap();
    assert_eq!(identity.len(), 1);
    assert_eq!(identity[0].data, original);
    let variants = elf::deployment_variants(&original, true).unwrap();
    let stripped = &variants[1].data;
    assert_eq!(stripped.len(), 144);
    assert_eq!(&stripped[64..], &original[64..144]);
    assert_eq!(elf::sectionless(stripped).unwrap(), *stripped);
    let mut overlapping = original.clone();
    overlapping[32..40].fill(0);
    assert!(elf::sectionless(&overlapping).is_err());
    let mut outside = original.clone();
    outside[96..104].copy_from_slice(&10000u64.to_le_bytes());
    assert!(elf::sectionless(&outside).is_err());
    let mut overflow = original.clone();
    overflow[80..88].copy_from_slice(&u64::MAX.to_le_bytes());
    assert!(elf::sectionless(&overflow).is_err());
    for packed in pack::pack_variants(
        &original,
        "x86_64-unknown-linux-gnu",
        Some(&["gzip-9".into(), "xz-bcj-6".into()]),
    )
    .unwrap()
    {
        assert_eq!(
            codec::decode(
                &packed.data[packed.payload_offset..],
                &packed.codec,
                original.len()
            )
            .unwrap(),
            original
        );
        assert_eq!(
            packed.data.len(),
            packed.loader_bytes + packed.payload_bytes
        );
    }
}

fn zero_tail_elf() -> Vec<u8> {
    let mut data = vec![0u8; 256 + 4096];
    data[..7].copy_from_slice(b"\x7fELF\x02\x01\x01");
    data[16..18].copy_from_slice(&2u16.to_le_bytes());
    data[18..20].copy_from_slice(&62u16.to_le_bytes());
    data[20..24].copy_from_slice(&1u32.to_le_bytes());
    data[24..32].copy_from_slice(&0x4000e8u64.to_le_bytes());
    data[32..40].copy_from_slice(&64u64.to_le_bytes());
    for (offset, value) in [(52, 64u16), (54, 56), (56, 3)] {
        data[offset..offset + 2].copy_from_slice(&value.to_le_bytes());
    }
    for (base, flags, offset, address, filesz, memsz) in [
        (64, 5u32, 0u64, 0x400000u64, 256u64, 256u64),
        (120, 6, 256, 0x401100, 4096, 8192),
    ] {
        data[base..base + 4].copy_from_slice(&1u32.to_le_bytes());
        data[base + 4..base + 8].copy_from_slice(&flags.to_le_bytes());
        for (field, value) in [
            (8, offset),
            (16, address),
            (32, filesz),
            (40, memsz),
            (48, 4096),
        ] {
            data[base + field..base + field + 8].copy_from_slice(&value.to_le_bytes());
        }
    }
    data[232..256].fill(0x90);
    data[256] = 17;
    data
}

#[test]
fn elf_zero_tail_preserves_loaded_data_and_rejects_unsafe_layouts() {
    let original = zero_tail_elf();
    let variants = elf::deployment_variants_with_options(&original, true, true).unwrap();
    let trimmed = &variants.last().unwrap().data;
    assert_eq!(trimmed.len(), 257);
    assert_eq!(elf::load_zero_tail(trimmed).unwrap(), None);
    // Independent loader model for the RW segment: initialized prefix followed
    // by zero-fill. Program-header bytes themselves are explicitly unobserved.
    let image = |data: &[u8]| {
        let size = u64::from_le_bytes(data[152..160].try_into().unwrap()) as usize;
        let memory = u64::from_le_bytes(data[160..168].try_into().unwrap()) as usize;
        let mut image = vec![0u8; memory];
        image[..size].copy_from_slice(&data[256..256 + size]);
        image
    };
    assert_eq!(image(&original), image(trimmed));
    assert_eq!(&original[232..257], &trimmed[232..257]);
    assert_eq!(&original[120..152], &trimmed[120..152]);
    assert_eq!(&original[160..176], &trimmed[160..176]);
    assert!(elf::deployment_variants_with_options(&original, false, true).is_err());
    for flags in [4u32, 7] {
        let mut bad = original.clone();
        bad[124..128].copy_from_slice(&flags.to_le_bytes());
        assert!(elf::load_zero_tail(&bad).is_err());
    }
    let mut shared_page = original.clone();
    shared_page[136..144].copy_from_slice(&0x400100u64.to_le_bytes());
    assert!(elf::load_zero_tail(&shared_page).is_err());
    let mut dynamic = original.clone();
    dynamic[176..180].copy_from_slice(&2u32.to_le_bytes());
    assert!(elf::load_zero_tail(&dynamic).is_err());
    let mut covered = original.clone();
    covered[176..180].copy_from_slice(&6u32.to_le_bytes());
    covered[208..216].copy_from_slice(&258u64.to_le_bytes());
    assert!(elf::load_zero_tail(&covered).is_err());
    let mut overflow = original.clone();
    overflow[160..168].copy_from_slice(&u64::MAX.to_le_bytes());
    assert!(elf::load_zero_tail(&overflow).is_err());
    assert!(elf::load_zero_tail(&original[..original.len() - 1]).is_err());
}

#[test]
fn actual_tcec_decoder_commands_restore_every_supported_envelope_family() {
    let sample = input();
    let directory = tempfile::tempdir().unwrap();
    for format in ["gzip", "bzip2", "alone", "xz", "raw"] {
        let mut recipe = Recipe::new(format);
        recipe.x86 = format == "raw";
        let blob = codec::compress(&sample, &recipe).unwrap();
        let command = envelope::decoder_command(&codec::decoder_for(&recipe).unwrap()).unwrap();
        let output = process::run(
            &command,
            &blob,
            directory.path(),
            &process::Limits::default(),
        )
        .unwrap();
        output.check(format).unwrap();
        assert_eq!(output.stdout, sample);
    }
    assert!(envelope::decoder_command("xz -d; echo unsafe").is_err());
}

fn fixture(directory: &Path, category: &str) -> (std::path::PathBuf, Vec<u8>) {
    let (artifact, spec, payload) = if category == "4k-elf" {
        (ordinary_elf(), Value::Null, Vec::new())
    } else {
        let payload = input();
        let compression = Recipe::new("xz");
        let blob = codec::compress(&payload, &compression).unwrap();
        let header = b"#!/bin/sh\ntail -n +3 \"$0\"|xz -d\n";
        let mut artifact = header.to_vec();
        artifact.extend(blob);
        (
            artifact,
            json!({"header_bytes":header.len(),"header_sha256":sha256(header),"decoder":"xz -d","payload_codec":compression}),
            payload,
        )
    };
    fs::write(directory.join("external-original"), &artifact).unwrap();
    let mut manifest = json!({"name":"owned-fixture","artifact":"missing-on-purpose","sha256":sha256(&artifact),"category":category});
    if !spec.is_null() {
        manifest["envelope"] = spec;
        manifest["payload_sha256"] = json!(sha256(&payload));
    }
    let path = directory.join("manifest.json");
    write_json(&path, &manifest).unwrap();
    (path, artifact)
}

#[test]
fn full_envelope_portfolio_replays_and_does_not_execute_submission() {
    let directory = tempfile::tempdir().unwrap();
    let (manifest, original) = fixture(directory.path(), "4k");
    let options = envelope::EnvelopeOptions {
        artifact: Some(directory.path().join("external-original")),
        notation: false,
        ..Default::default()
    };
    let out = directory.path().join("search");
    let summary = envelope::run(&manifest, &out, &options).unwrap();
    assert_eq!(summary["candidates"], 332);
    assert_eq!(summary["no_size_regression"], true);
    assert_eq!(summary["uci"]["status"], "not_run");
    assert!(summary["accepted"].is_null());
    assert!(summary["manifest"]["envelope"].get("header").is_none());
    let mut invalid = summary["manifest"]["envelope"].clone();
    invalid["header_sha256"] = json!("changed");
    assert!(envelope::extract(&original, &invalid).is_err());
    let replay = envelope::reproduce(
        &out.join("summary.json"),
        &directory.path().join("replay"),
        "smallest",
    )
    .unwrap();
    assert_eq!(replay["byte_replay"], "pass");
    assert_eq!(replay["sha256"], summary["winner"]["sha256"]);
    assert_eq!(
        fs::read(directory.path().join("external-original")).unwrap(),
        original
    );
    let mut altered = summary;
    altered["tool"]["executable_sha256"] = json!("different");
    write_json(&out.join("changed.json"), &altered).unwrap();
    assert!(envelope::reproduce(
        &out.join("changed.json"),
        &directory.path().join("rejected"),
        "smallest"
    )
    .is_err());
}

#[test]
fn elf_category_never_emits_script_wrappers() {
    let directory = tempfile::tempdir().unwrap();
    let (manifest, original) = fixture(directory.path(), "4k-elf");
    let options = envelope::EnvelopeOptions {
        artifact: Some(directory.path().join("external-original")),
        notation: false,
        ..Default::default()
    };
    let out = directory.path().join("identity");
    let summary = envelope::run(&manifest, &out, &options).unwrap();
    assert_eq!(summary["candidates"], 1);
    assert_eq!(fs::read(out.join("smallest")).unwrap(), original);
    let mut value: Value = serde_json::from_slice(&fs::read(&manifest).unwrap()).unwrap();
    value["allow_section_header_removal"] = json!(true);
    write_json(&manifest, &value).unwrap();
    let out = directory.path().join("sections");
    let summary = envelope::run(&manifest, &out, &options).unwrap();
    assert_eq!(summary["winner"]["bytes"], 144);
    assert!(fs::read(out.join("smallest"))
        .unwrap()
        .starts_with(b"\x7fELF"));
    assert_eq!(summary["winner"]["recipe"]["pack_id"], "raw");
}
