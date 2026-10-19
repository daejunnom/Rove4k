#![no_std]

// Compile with --edition=2021. A native object crosses the C ABI boundary;
// no Rust layout, allocator, standard library or unwinding crosses it.
#[no_mangle]
pub extern "C" fn nv_popcount64(bits: u64) -> u32 {
    bits.count_ones()
}
