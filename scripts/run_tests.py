import sys, traceback
sys.path.insert(0, ".")
import tests.test_bt_engine as t
FNS = [t.test_ema_seed_and_cross, t.test_no_lookahead_turtle, t.test_sl_tp_and_costs,
       t.test_trailing_and_breakeven, t.test_backtest_reproducible_and_metrics,
       t.test_validator, t.test_montecarlo_seed, t.test_turtle_close_never_triggers_on_own_high,
       t.test_turtle_exact_numbers, t.test_empty_backtest_has_no_id, t.test_vwap_only_in_session,
       t.test_enriched_trade_fields, t.test_turtle_variants_differ, t.test_vwap_first_bucket_blocked,
       t.test_spike_filter_off_by_default, t.test_equity_incluye_flotante,
       t.test_vwap_exit_solo_en_sesion, t.test_vwap_sesiones_horario_verano,
       t.test_cuenta_en_cero_para, t.test_margen_mira_flotante,
       t.test_vwap_aplana_fin_sesion, t.test_vwap_m15_ref_dos_velas, t.test_vwap_solo_cruce,
       t.test_vwap_rr_stop_objetivo]
ok = fail = 0
for fn in FNS:
    try:
        fn()
        print(f"PASS {fn.__name__}")
        ok += 1
    except Exception:
        print(f"FAIL {fn.__name__}")
        traceback.print_exc()
        fail += 1
print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
