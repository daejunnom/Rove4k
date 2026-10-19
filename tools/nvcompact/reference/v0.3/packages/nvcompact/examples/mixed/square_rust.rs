#![no_std]

#[no_mangle]
pub extern "C" fn nv_square_bonus(square: u32) -> i32 {
    // The shared contract restricts square to 0..64 (exclusive upper bound).
    // Each intermediate lies in -7..=7, so these abs operations cannot overflow.
    let file = (square & 7) as i32;
    let rank = (square >> 3) as i32;
    8 - (2 * file - 7).abs() - (2 * rank - 7).abs()
}
