#!/usr/bin/env python3
"""
Smoke test for the rep channel — the plumbing that carries knocks, judged
replies, and scheduled pushes. Drives the REAL production functions against a
sandbox copy of the repo with the outside-world boundaries stubbed: the LLM call,
the TTS render (audio scenarios only), push_to_phone, and commit_and_push. No
secrets, no network, no writes outside the sandbox. CI runs it on any push that touches the machinery (smoke.yml);
locally:

  python scripts/smoke_test.py

A fixed bug becomes a case here the day it's fixed:
  #1  queue drain: oldest-due fires first, one non-forced per tick (2026-07-03)
  #2  prose-wrapped LLM JSON killed a knock tick (2026-07-04)
  #3  chained follow-up overwrote the original ask; chat lost chained replies (2026-07-06)
  #4  hinted-forever: reveal-capped fires now graduate cross-day (2026-07-08)
  #5  volley knock: binding targets + deterministic chain advance (2026-07-08)
  #6  eavesdrop dose: catch replies move recognition only, never production (2026-07-09)
  #7  stale clone read yesterday's story; comma-joined soak payload never matched (2026-07-15)
  #8  [SFX] lines silently dropped by the renderer — now a beat of air (2026-07-18)
  #9  special_* string-mission sidecar crashed the ticket sort; the ticket now
      smoke-runs end-to-end on day-zero state (2026-07-19, inbox item)
  #10 two renders shared one scratch dir — the first to finish deleted it under
      the second, losing a draft episode; hosts without secrets now skip
      instead of retrying hourly (2026-07-23)
  #11 an eavesdrop tape hearsayed about an unnamed அவங்க and the drift question
      asked WHO — unanswerable from the audio; the thread-blind catch judge then
      re-asked a catch that had already landed on turn 1 (2026-07-25)
  #12 the deck selector had no staleness term: tier → ripeness → alphabetical
      froze the head of every tier, 45 of 70 fire items were never asked once,
      and cold/total reported a winning sprint throughout (2026-07-25)
"""
import sys
import os
import tempfile
from pathlib import Path

# The harness lives in scripts/smoke/_fixtures.py (spine plan §10). Names that
# are never rebound come across directly — and MUST, for `mechanism` and the
# line counters: s18's guard matches them as bare calls, so reaching them
# through the module would make that guard silently stop counting these cases.
# The three that ARE rebound at run time — pb, wr, si — are reached through
# `fx` and nowhere else. See the module docstring for why.
from smoke import _fixtures as fx
from smoke import compose
from smoke import knock
from smoke import publish
from smoke import queue
from smoke import ratchets
from smoke import render
from smoke import state
from smoke._fixtures import (
    load_modules, make_sandbox, run, snapshot,
)


def main():
    """Dispatch. One sandbox and one set of module objects for the whole run:
    the cases are being re-homed, not re-scoped, and a per-file sandbox would
    hand each file its own re-imported `mk` — the one thing §10.7 says not to
    do, since every stub and its teardown are keyed to a module object."""
    with tempfile.TemporaryDirectory(prefix="tamil-smoke-") as tmp:
        sb = make_sandbox(Path(tmp))
        print(f"sandbox: {sb}")
        # Every case below that drives kr.main() is simulating a REPLY to a
        # knock, so it says so (2026-08-28). Untagged now means MESSAGE — the
        # routing split's deliberate default — and without this the whole suite
        # would silently re-route into the message lane and stop testing the
        # judges. s83 owns the untagged case and sets this itself.
        os.environ["REPLY_INTENT"] = "reply"
        mk, kr, pq = load_modules(sb)
        snapshot(mk, kr, pq, fx.pb, fx.wr, fx.si)
        run(compose.s1_parse_llm_json, mk)
        run(knock.s2_rails_gate, mk, sb / "progress" / "knock_log.json")
        run(publish.s15_push_retry, mk)
        run(knock.s67_two_replies_to_one_knock_both_survive, mk)
        run(publish.s35_quiet_hours_chokepoint, sb)
        run(knock.s59_transit_bit, mk, sb)
        run(knock.s3_knock_paths, mk, sb)
        run(knock.s4_normalize, kr)
        run(knock.s5_reply_judge, mk, kr, sb)
        run(publish.s6_queue_drain, mk, pq, sb)
        run(state.s7_integrity, sb)
        run(knock.s8_variety_and_decay, mk, kr, sb)
        run(knock.s9_audio_knock_feed, mk, sb)
        run(knock.s10_chain_history, mk, kr, sb)
        run(knock.s11_capped_graduation, kr, sb)
        run(knock.s12_volley, mk, kr, sb)
        run(knock.s13_eavesdrop, mk, kr, sb)
        run(knock.s14_reply_correlation, kr)
        run(state.s16_stale_clone_gates, sb)
        run(knock.s17_campaign_digest, mk, sb)
        run(ratchets.s18_size_budgets, mk, kr, sb)
        run(knock.s20_fielding, mk, kr, sb)
        run(knock.s21_volley_represent, kr, sb)
        run(publish.s22_sfx_pause, sb)
        run(publish.s23_ticket_end_to_end, sb)
        run(publish.s25_studio_concurrency_and_secrets, sb)
        run(render.s26_capacity_routing, sb)
        run(knock.s27_schedule_and_soak_guards, sb)
        run(render.s28_cloud_writer, sb)
        run(queue.s29_one_runner_every_capability, mk, pq, kr, sb)
        run(knock.s30_anna_speaks_back, mk, kr, sb)
        run(publish.s31_feed_carries_every_pushed_dose, sb)
        run(state.s32_pool_rotation_and_coverage, mk, sb)
        run(state.s33_catch_response_pairs, mk, sb)
        run(state.s34_focus_and_background, sb)
        run(state.s36_soak_order_carries_shape, sb)
        run(state.s37_repair_earns_the_dose, sb)
        run(state.s38_teach_enters_the_lexicon, sb)
        run(state.s39_ticket_carries_the_commission, sb)
        run(render.s40_drill_consumes_its_commission, sb)
        run(state.s41_slip_ledger, kr, sb)
        run(state.s42_session_log_one_row_per_day, sb)
        run(publish.s43_sidecar_callback_never_drops_silently, sb)
        run(state.s44_a_commission_can_discharge_the_flag, sb)
        run(queue.s45_concurrent_appends_merge, mk, sb)
        run(state.s46_the_commission_notice_names_the_debt, sb)
        run(state.s47_hinted_retest_rule, sb)
        run(state.s53_evidence_gates_the_ear, sb)
        run(state.s54_no_deadline_reaches_any_surface, sb)
        run(state.s55_demotion_survives_the_close, sb)
        run(state.s56_timezone_is_one_dial, sb)
        run(render.s48_drill_answer_key_lint, sb)
        run(render.s57_rotation_tape, sb)
        run(compose.s58_a_sheet_survives_a_model_thinking_out_loud, sb)
        run(knock.s49_thread_continuity, mk, kr, sb)
        run(knock.s50_read_surfaces_are_phonetic, mk, kr, sb)
        run(knock.s51_derived_files_are_rerendered_not_merged, mk, sb)
        run(knock.s84_a_turn_is_filed_under_the_day_it_happened, mk, sb)
        run(ratchets.s52_andrew_is_family_already, sb)
        run(ratchets.s78_the_open_gives_before_it_takes, sb)
        run(state.s71_a_new_record_is_born_reachable, sb)
        run(knock.s60_the_ear_meter, kr, sb)
        run(knock.s81_the_ear_judge_stamps_its_own_evidence, kr, sb)
        run(knock.s82_the_catch_lane_has_a_mouth, mk, kr, sb)
        run(knock.s83_reply_or_message_is_decided_by_the_tag, mk, kr, sb)
        run(knock.s61_no_number_is_recited_at_him, kr, sb)
        run(state.s62_the_return_clock_is_keyed_to_the_ear, sb)
        run(state.s63_the_machines_reach_the_ticket)
        run(state.s64_the_ask_cooldown_covers_the_session_lane, sb)
        run(state.s65_the_ordering_outlives_the_deck, sb)
        run(state.s76_the_ear_queue_is_not_the_catch_tag, sb)
        run(state.s77_the_wild_line_reaches_the_session, sb)
        run(compose.s66_json_mode_is_actually_sent, mk, kr, sb)
        run(publish.s68_the_convergence_audit_fixes, sb)
        run(state.s69_two_readers_two_tickets, sb)
        run(compose.s70_the_executor_is_chosen_by_the_host, sb)
        run(ratchets.s72_a_stub_never_outlives_its_case, mk, kr)
        run(publish.s73_one_tail_for_the_render_family, sb)
        run(publish.s74_a_derived_file_follows_its_source, sb)
        run(state.s79_a_rating_lands_or_says_why, sb)
        run(state.s80_one_produced_resolver, sb)
        run(ratchets.s75_the_stack_is_one_way)
        run(ratchets.s85_the_fixture_record_tracks_the_minted_one, sb)
        run(state.s86_a_tape_is_not_a_teacher, sb)
        run(state.s87_form_is_a_choice_per_order, sb)

    if fx.ONLY and not fx.RAN:
        sys.exit(f"no case matched {fx.ONLY} — name a case (s41) or a prefix (s41_slip)")
    scope = (f"{len(fx.RAN)} case(s): {', '.join(fx.RAN)}" if fx.ONLY
             else f"{len(fx.RAN)} cases")
    print(f"\n{scope}")
    print(f"{'ALL GREEN' if not fx.FAILURES else 'FAILURES: ' + ', '.join(fx.FAILURES)}")
    sys.exit(1 if fx.FAILURES else 0)


if __name__ == "__main__":
    main()
