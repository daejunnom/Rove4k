#![no_std]

// The C ABI driver validates index < 8192; one process and no concurrent calls.
static mut STATE: [u8; 8192] = {
    let mut data = [0; 8192];
    data[0] = 17;
    data
};

#[no_mangle]
/// # Safety
/// The caller must provide index < 8192 and prevent concurrent access.
pub unsafe extern "C" fn nv_probe(index: u32, value: u32) -> u32 {
    // The pointer remains within STATE for the declared input domain. Volatile
    // accesses keep this initialized state observable to the independent probe.
    unsafe {
        let slot = core::ptr::addr_of_mut!(STATE)
            .cast::<u8>()
            .add(index as usize);
        let before = slot.read_volatile();
        slot.write_volatile(value as u8);
        before as u32
    }
}
