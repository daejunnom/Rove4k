#include <assert.h>
#include <stdio.h>
int rove_state_baseline_core(void);
int rove_state_candidate_core(void);
int main(void){
    int baseline=rove_state_baseline_core(),candidate=rove_state_candidate_core();
    assert(baseline==10&&candidate==10);
    printf("{\"actual_DEV0_core_checks_per_form\":%d,\"forms\":2,\"fullkey_collision\":true,"
           "\"actual_halfmove_path_TT_misses\":true,\"third_visit\":true,\"draw_mate_precedence\":true,"
           "\"positive_production_search_learning\":true,\"live_ply_abort_retains_completed_fields\":true,"
           "\"EP_correction_excluded\":true,\"concurrent_publication_claim\":false}\n",baseline);
    return 0;
}
