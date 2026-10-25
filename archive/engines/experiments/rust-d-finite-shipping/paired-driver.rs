// Independent std diagnostic, not a no_std production/runtime ELF.
#[cfg(not(tiny_shipping))]compile_error!("paired diagnostic requires tiny_shipping");
#[cfg(tiny_dev)]compile_error!("paired diagnostic excludes tiny_dev");
pub const HQ:bool=true;
mod board;
mod old_search;
mod new_search;

mod os {
    use std::sync::atomic::{AtomicU64,Ordering};
    static CLOCK:AtomicU64=AtomicU64::new(0);
    static READS:AtomicU64=AtomicU64::new(0);
    pub fn set_clock(value:u64){CLOCK.store(value,Ordering::Relaxed);}
    pub fn clock_reads()->u64{READS.load(Ordering::Relaxed)}
    pub fn millis()->u64{READS.fetch_add(1,Ordering::Relaxed);CLOCK.load(Ordering::Relaxed)}
    pub fn allocate(bytes:usize)->*mut u8 {
        let layout=std::alloc::Layout::from_size_align(bytes,4096).unwrap();
        let ptr=unsafe{std::alloc::alloc_zeroed(layout)};
        assert!(!ptr.is_null());ptr
    }
}

fn correction_digest(values:&[i16;1024])->u64 {
    values.iter().fold(1469598103934665603,|hash,&value|
        (hash^value as u16 as u64).wrapping_mul(1099511628211))
}

fn main(){
    let old=old_search::finite_probe::depth_two();
    let new=new_search::finite_probe::depth_two();
    assert_eq!(old,new,"complete Result/local nodes/correction witness differs");
    let budget=old_search::finite_probe::default_budget_two();
    let shipping=new_search::finite_probe::three_claims_with_budget_two();
    assert_eq!(shipping,(3,3,false),"shipping must omit unsupported global quota");
    let stopped=new_search::finite_probe::pre_stopped();
    let deadline=new_search::finite_probe::deadline_boundary();
    assert_eq!(stopped,(0,0,true));
    assert_eq!(deadline,(256,1,2,true));
    println!(concat!("{{\"passed\":true,\"image_class\":\"independent std paired diagnostic\",",
        "\"hq\":true,\"fixed_depth\":2,\"best\":{},\"score\":{},\"completed_depth\":{},",
        "\"result_nodes\":{},\"worker_nodes\":{},\"old_new_complete_result_equal\":true,",
        "\"correction_equal\":true,\"correction_digest\":\"{:016x}\",\"frozen_preserved\":true,",
        "\"default_budget_accepted\":{},\"default_budget_local\":{},\"default_budget_global\":{},",
        "\"default_budget_stopped\":{},\"shipping_budget_accepted\":{},\"shipping_budget_local\":{},",
        "\"shipping_budget_stopped\":{},\"pre_stopped_local\":{},\"pre_stopped_clock_reads\":{},",
        "\"pre_stopped_stop\":{},\"deadline_local\":{},\"deadline_reads_before_boundary\":{},",
        "\"deadline_reads_after_boundary\":{},\"deadline_stop\":{}}}"),
        old.0,old.1,old.2,old.3,old.4,correction_digest(&old.5),
        budget.0,budget.1,budget.2,budget.3,shipping.0,shipping.1,shipping.2,
        stopped.0,stopped.1,stopped.2,deadline.0,deadline.1,deadline.2,deadline.3);
}
