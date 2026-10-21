// Owned static-advice example. No crate build, macro expansion or execution.
pub fn bounded_rank(to: i32) -> bool {
    if to < 0 || to > 127 {
        return false;
    }
    (to >> 4) == 0 || (to >> 4) == 7
}

pub fn bounded_mask(x: u32) -> u32 {
    if x > 7 {
        return 0;
    }
    x & 7
}

pub fn checked_increment(x: u32) -> u32 {
    if x > 7 {
        return 0;
    }
    x + 1
}

pub fn unsupported_method(x: i32) -> i32 {
    x.wrapping_add(1) // A method call is outside this primitive subset.
}
