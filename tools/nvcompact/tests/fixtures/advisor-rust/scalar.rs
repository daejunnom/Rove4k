// Self-owned, inert Rust scalar examples. Advice never executes this source.
// The declarations intentionally include unused bindings and repeated values.

pub fn edge(to: i32) -> bool {
    if to < 0 || to > 127 {
        return false;
    }
    if to & 136 != 0 {
        return false;
    }
    (to >> 4) == 0 || (to >> 4) == 7
}

pub fn mask(x: i32) -> i32 {
    if x < 0 || x > 7 {
        return 0;
    }
    x & 7
}

pub fn finite_flag(x: u32) -> bool {
    let low: u32 = x & 1;
    low == 0
}

pub fn repeated(x: u64, unused: i32) -> u64 {
    let spare: i32 = 0;
    let a: u64 = x & 0x5555555555555555u64;
    a | 0x5555555555555555u64
}

pub fn narrow(x: u32) -> i32 {
    let high: u32 = (x & 1) + 4294967294u32;
    high as i32
}
