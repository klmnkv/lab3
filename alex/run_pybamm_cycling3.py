"""
PyBaMM long-term cycling: WLTP power profile for trolleybus.
SPMe + SEI + Li plating, OKane2022 parameters (LG M50).

v2: ALL cycles in ONE solve() call — degradation accumulates correctly.
    Real-time progress via PyBaMM callbacks.
    return_solution_if_failed_early=True for crash recovery.
"""
import pybamm
import numpy as np
import pandas as pd
import os
import sys
import time
from datetime import timedelta

# =============================================================
#                  USER CONFIGURATION
# =============================================================
PACK_ENERGY_KWH   = 90       # Pack energy [kWh] -> cell count
SOC_UPPER_PCT     = 95       # Charge to [%]
SOC_LOWER_PCT     = 20       # Discharge to [%]
N_CYCLES          = 100      # Total macro-cycles
CHARGE_CURRENT_A  = 2.45     # Charge CC current [A per cell]
WLTP_POINTS       = 1522     # Downsample WLTP profile
T_AMBIENT_C       = 25       # Ambient temperature [degC]
# =============================================================

SOC_UPPER = SOC_UPPER_PCT / 100.0
SOC_LOWER = SOC_LOWER_PCT / 100.0

CAPACITY_AH = 4.9
V_NOM       = 3.63
V_MIN_ABS   = 2.5
V_MAX_ABS   = 4.2

SOC_TABLE = np.array([0.00, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40,
                       0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 1.00])
OCV_TABLE = np.array([2.50, 3.00, 3.20, 3.30, 3.38, 3.50, 3.58,
                       3.65, 3.72, 3.82, 3.95, 4.08, 4.14, 4.20])

def soc_to_voltage(soc):
    return float(np.interp(soc, SOC_TABLE, OCV_TABLE))

def voltage_to_soc(v):
    return float(np.interp(v, OCV_TABLE, SOC_TABLE)) * 100

T_AMBIENT_K = T_AMBIENT_C + 273.15
V_UPPER = soc_to_voltage(SOC_UPPER)
V_LOWER = soc_to_voltage(SOC_LOWER)
E_CELL_WH = V_NOM * CAPACITY_AH
N_CELLS = int(round(PACK_ENERGY_KWH * 1000 / E_CELL_WH))
N_SERIES = int(round(540 / V_NOM))
N_PARALLEL = max(1, int(round(N_CELLS / N_SERIES)))
N_CELLS = N_SERIES * N_PARALLEL
CHARGE_CRATE = CHARGE_CURRENT_A / CAPACITY_AH

# =====================================================================
#  Progress callback — prints one line per cycle during solve()
# =====================================================================
class CycleProgressCallback(pybamm.callbacks.Callback):
    """Print progress after each macro-cycle during a single solve()."""

    def __init__(self, initial_capacity_ah=None):
        self.t0 = time.time()
        self.cap0 = initial_capacity_ah   # set after first cycle

    def on_cycle_end(self, logs):
        cyc_now, cyc_total = logs["cycle number"]
        elapsed = time.time() - self.t0
        avg = elapsed / cyc_now
        eta = avg * (cyc_total - cyc_now)

        sv = logs.get("summary variables")
        cap_str = ""
        soh_str = ""
        li_str  = ""
        if sv is not None:
            try:
                d = sv.get_summary_variables()
                cap = d.get("Capacity [A.h]")
                if cap is not None:
                    cap = float(cap)
                    if self.cap0 is None:
                        self.cap0 = cap
                    soh = cap / self.cap0 * 100
                    cap_str = f"Cap={cap:.3f}Ah"
                    soh_str = f"SoH={soh:.2f}%"

                li_sei = d.get("Loss of lithium to negative SEI [mol]")
                li_plt = d.get("Loss of lithium to negative lithium plating [mol]")
                if li_sei is not None and li_plt is not None:
                    li_str = (f"Li_SEI={float(li_sei):.2e} "
                              f"Li_plt={float(li_plt):.2e}")
            except Exception:
                pass

        eta_str = str(timedelta(seconds=int(eta)))
        print(f"  Cycle {cyc_now:3d}/{cyc_total}  "
              f"{cap_str}  {soh_str}  {li_str}  "
              f"[{elapsed:.0f}s, ~{avg:.1f}s/cyc, ETA {eta_str}]",
              flush=True)


pybamm.set_logging_level("WARNING")

print("=" * 70)
print("    PyBaMM Battery Cycling v3 — Trolleybus Simulink profile")
print("=" * 70)
print(f"PyBaMM version: {pybamm.__version__}")
print(f"\n--- Pack ---")
print(f"  Energy:       {PACK_ENERGY_KWH} kWh")
print(f"  Cell:         LG M50, {CAPACITY_AH} Ah, {V_NOM} V")
print(f"  N cells:      {N_CELLS}  ({N_SERIES}s x {N_PARALLEL}p)")
print(f"  Pack voltage: {N_SERIES*V_NOM:.0f} V nom")
print(f"  Pack cap:     {N_PARALLEL*CAPACITY_AH:.1f} Ah")
print(f"\n--- Limits ---")
print(f"  SoC upper:    {SOC_UPPER_PCT}%  ->  OCV ~ {V_UPPER:.3f} V")
print(f"  SoC lower:    {SOC_LOWER_PCT}%  ->  OCV ~ {V_LOWER:.3f} V")
print(f"  Usable:       {SOC_UPPER_PCT - SOC_LOWER_PCT}%  "
      f"= {(SOC_UPPER - SOC_LOWER)*PACK_ENERGY_KWH:.1f} kWh")
print(f"\n--- Charge ---")
print(f"  Current:      {CHARGE_CURRENT_A} A ({CHARGE_CRATE:.2f}C)")
print(f"  CC to:        {V_UPPER:.3f} V, CV to C/20 ({CAPACITY_AH/20:.3f} A)")
print(f"\n--- Cycling ---")
print(f"  N cycles:     {N_CYCLES}")
print(f"  T ambient:    {T_AMBIENT_C} degC")

if len(sys.argv) > 1:
    work_dir = sys.argv[1]
else:
    work_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(work_dir)

# =================================================================
# [1/4] Load and downsample WLTP
# =================================================================
print(f"\n[1/4] Loading WLTP profile...")
wltp = pd.read_csv("wltp_profile1.csv")
t_raw = wltp["time_s"].values.astype(float)
P_raw = wltp["power_W"].values.astype(float)

t_ds = np.linspace(t_raw[0], t_raw[-1], WLTP_POINTS)
P_ds = np.interp(t_ds, t_raw, P_raw)
P_cell = P_ds / N_CELLS
print(f"  {len(t_raw)} -> {WLTP_POINTS} pts, {t_raw[-1]:.0f} s")
print(f"  Cell power: {P_cell.min():.2f} .. {P_cell.max():.2f} W")

E_wltp_net = np.trapezoid(P_cell, t_ds) / 3600
E_wltp_dis = np.trapezoid(np.maximum(P_cell, 0), t_ds) / 3600
E_wltp_reg = np.trapezoid(np.minimum(P_cell, 0), t_ds) / 3600
soc_per_wltp = E_wltp_net / (V_NOM * CAPACITY_AH)
usable_soc = SOC_UPPER - SOC_LOWER
n_wltp_est = usable_soc / soc_per_wltp if soc_per_wltp > 0 else 1
N_WLTP = int(np.ceil(n_wltp_est)) + 3
print(f"  Energy/WLTP:  {E_wltp_net:.3f} Wh net "
      f"(dis {E_wltp_dis:.3f}, regen {E_wltp_reg:.3f})")
print(f"  ~{soc_per_wltp*100:.1f}% SoC net per WLTP")
print(f"  WLTPs/cycle:  ~{n_wltp_est:.0f} (max {N_WLTP})")

t_wltp_0 = t_ds - t_ds[0]
drive_cycle_single = np.column_stack([t_wltp_0, P_cell])

# =================================================================
# [2/4] Model + experiment
# =================================================================
print(f"\n[2/4] Setting up model and experiment...")
model = pybamm.lithium_ion.SPMe(
    options={
        "SEI": "solvent-diffusion limited",
        "lithium plating": "irreversible",
        "thermal": "lumped",
    }
)
param = pybamm.ParameterValues("OKane2022")
param["Nominal cell capacity [A.h]"] = CAPACITY_AH
param["Ambient temperature [K]"] = T_AMBIENT_K
param["Lithium plating kinetic rate constant [m.s-1]"] = 1e-11
param["Lithium plating transfer coefficient"] = 0.5
print("  SPMe + SEI + Li plating + lumped thermal, OKane2022")

# --- Build one macro-cycle ---
discharge_steps = []
for i in range(N_WLTP):
    discharge_steps.append(
        pybamm.step.power(
            drive_cycle_single,
            termination=f"< {V_MIN_ABS} V",
            direction="discharge",
        )
    )
    discharge_steps.append(
        pybamm.step.rest(
            duration="10 s",
            termination=f"< {V_LOWER:.4f} V",
        )
    )

charge_steps = [
    pybamm.step.rest(duration="60 s"),
    f"Charge at {CHARGE_CURRENT_A} A until {V_UPPER:.4f} V",
    f"Hold at {V_UPPER:.4f} V until C/20",
    pybamm.step.rest(duration="60 s"),
]

single_cycle = tuple(discharge_steps + charge_steps)
n_discharge_steps = len(discharge_steps)
n_charge_steps = len(charge_steps)
n_steps_per_cycle = len(single_cycle)
print(f"  Steps/cycle: {n_steps_per_cycle} "
      f"({N_WLTP} WLTPs + rests + {n_charge_steps} charge)")

# --- Full experiment: all cycles at once ---
experiment = pybamm.Experiment([single_cycle] * N_CYCLES)
print(f"  Total experiment: {N_CYCLES} cycles x {n_steps_per_cycle} steps "
      f"= {N_CYCLES * n_steps_per_cycle} steps")

# --- Solver with crash recovery ---
solver = pybamm.CasadiSolver(
    mode="safe",
    return_solution_if_failed_early=True,
)

sim = pybamm.Simulation(
    model,
    parameter_values=param,
    experiment=experiment,
    solver=solver,
)

# =================================================================
# [3/4] SOLVE — all cycles in one call
# =================================================================
print(f"\n[3/4] Solving {N_CYCLES} cycles (single solve call)...")
print("=" * 70)

callback = CycleProgressCallback()
t_start = time.time()

try:
    sol = sim.solve(initial_soc=SOC_UPPER, callbacks=callback)
except pybamm.SolverError as e:
    print(f"\n>>> SOLVER ERROR at some cycle!")
    print(f">>> {str(e)[:300]}")
    sol = getattr(sim, '_solution', None)
    if sol is None:
        sol = getattr(sim, 'solution', None)
except KeyboardInterrupt:
    print(f"\n>>> INTERRUPTED by user (Ctrl+C)")
    sol = getattr(sim, '_solution', None)
    if sol is None:
        sol = getattr(sim, 'solution', None)
except Exception as e:
    print(f"\n>>> UNEXPECTED ERROR: {type(e).__name__}: {str(e)[:300]}")
    sol = getattr(sim, '_solution', None)
    if sol is None:
        sol = getattr(sim, 'solution', None)

t_solve = time.time() - t_start

if sol is None or not hasattr(sol, 'cycles') or len(sol.cycles) == 0:
    print("\n!!! NO DATA recovered. Exiting.")
    sys.exit(1)

n_completed = len(sol.cycles)
print(f"\n{'=' * 70}")
print(f"  Solve done: {n_completed}/{N_CYCLES} cycles in "
      f"{timedelta(seconds=int(t_solve))}")
print(f"{'=' * 70}")

# =================================================================
# [4/4] Post-process — extract data from sol.cycles
# =================================================================
print(f"\n[4/4] Extracting data from {n_completed} cycles...")

xlsx_path = "pybamm_results.xlsx"
vol_sel = set([1,2,5,10,25,50,100,150,200,250,300,350,400,450,500])
MAX_VOLTAGE_PTS = 5000   # downsample voltage curves

all_rows = []
all_voltage = []
initial_Q_dis = None

for ci in range(n_completed):
    cyc = sol.cycles[ci]
    global_cycle = ci + 1

    # --- Cycle-level arrays ---
    try:
        t_c = cyc["Time [s]"].entries.flatten()
        V_all = cyc["Voltage [V]"].entries.flatten()
        I_all = cyc["Current [A]"].entries.flatten()
        T_all = cyc["Cell temperature [K]"].entries.flatten()
    except Exception as e:
        print(f"  Cycle {global_cycle}: SKIP (data error: {e})")
        continue

    # --- Q, E ---
    Q_dis = np.trapezoid(np.maximum(I_all, 0), t_c) / 3600
    Q_cha = np.trapezoid(np.maximum(-I_all, 0), t_c) / 3600
    E_dis = np.trapezoid(np.maximum(I_all, 0) * V_all, t_c) / 3600
    E_cha = np.trapezoid(np.maximum(-I_all, 0) * V_all, t_c) / 3600

    if initial_Q_dis is None and Q_dis > 0.1:
        initial_Q_dis = Q_dis
    current_soh = Q_dis / initial_Q_dis * 100 if initial_Q_dis else 100.0
    soh_fade = 100.0 - current_soh

    # --- Count WLTPs (discharge steps with meaningful data) ---
    steps = cyc.steps
    wltp_count = 0
    for s_idx in range(0, n_discharge_steps, 2):
        if s_idx >= len(steps):
            break
        try:
            t_s = steps[s_idx]["Time [s]"].entries.flatten()
            if len(t_s) >= 2 and (t_s[-1] - t_s[0]) >= 1.0:
                wltp_count += 1
        except Exception:
            break

    # --- Degradation variables ---
    deg_names = [
        "Loss of lithium to negative SEI [mol]",
        "Loss of lithium to negative lithium plating [mol]",
        "X-averaged negative SEI thickness [m]",
        "X-averaged negative electrode porosity",
        "X-averaged positive electrode porosity",
        "Negative electrode capacity [A.h]",
        "Positive electrode capacity [A.h]",
        "Discharge capacity [A.h]",
        "Throughput capacity [A.h]",
    ]

    # --- SoC estimation from OCV (voltage at rest, I≈0) ---
    rest_mask = np.abs(I_all) < 0.05
    V_start = float(V_all[0])  # start of cycle = after prev charge rest
    # End-of-discharge: lowest V during rest before charge phase
    # Find index where charging begins (I goes negative significantly)
    charge_idx = np.where(I_all < -0.5)[0]
    if len(charge_idx) > 0:
        pre_charge = charge_idx[0]
        # Look for rest voltage just before charge
        rest_before_charge = np.where(rest_mask[:pre_charge])[0]
        if len(rest_before_charge) > 0:
            V_end_dis = float(V_all[rest_before_charge[-1]])
        else:
            V_end_dis = float(V_all[pre_charge])
    else:
        V_end_dis = float(V_all.min())

    row = {
        "cycle": global_cycle,
        "n_wltp": wltp_count,
        "SoC_start_pct": round(voltage_to_soc(V_start), 2),
        "SoC_end_dis_pct": round(voltage_to_soc(V_end_dis), 2),
        "Q_discharge_Ah": round(Q_dis, 5),
        "Q_charge_Ah": round(Q_cha, 5),
        "SoH_pct": round(current_soh, 3),
        "SoH_fade_pct": round(soh_fade, 4),
        "coulombic_eff_pct": round(Q_dis/Q_cha*100, 3) if Q_cha > 1e-9 else 0,
        "E_discharge_Wh": round(E_dis, 4),
        "E_charge_Wh": round(E_cha, 4),
        "energy_eff_pct": round(E_dis/E_cha*100, 3) if E_cha > 1e-9 else 0,
        "V_min_V": round(float(V_all.min()), 5),
        "V_max_V": round(float(V_all.max()), 5),
        "V_mean_dis_V": round(float(np.mean(V_all[I_all > 0])), 5)
                        if np.any(I_all > 0) else 0,
        "I_max_A": round(float(I_all.max()), 4),
        "I_min_A": round(float(I_all.min()), 4),
        "T_max_C": round(float(T_all.max()) - 273.15, 3),
        "T_min_C": round(float(T_all.min()) - 273.15, 3),
        "T_mean_C": round(float(T_all.mean()) - 273.15, 3),
        "dT_K": round(float(T_all.max() - T_all.min()), 3),
        "cycle_time_s": round(float(t_c[-1] - t_c[0]), 2),
    }

    for vn in deg_names:
        try:
            val = cyc[vn].entries.flatten()[-1]
            safe = vn.replace("[", "").replace("]", "").replace(".", "")
            row[safe] = round(float(val), 8)
        except Exception:
            pass

    all_rows.append(row)

    # --- Voltage curves for selected cycles ---
    if global_cycle in vol_sel:
        n_pts = len(t_c)
        if n_pts > MAX_VOLTAGE_PTS:
            idx = np.linspace(0, n_pts - 1, MAX_VOLTAGE_PTS, dtype=int)
        else:
            idx = np.arange(n_pts)
        n_min = min(len(t_c[idx]), len(V_all[idx]),
                    len(I_all[idx]), len(T_all[idx]))
        all_voltage.append(pd.DataFrame({
            "cycle": global_cycle,
            "time_s": t_c[idx][:n_min] - t_c[idx][0],
            "voltage_V": V_all[idx][:n_min],
            "current_A": I_all[idx][:n_min],
            "temperature_K": T_all[idx][:n_min],
        }))

    # Brief progress every 10 cycles
    if global_cycle % 10 == 0 or global_cycle == n_completed:
        print(f"  Processed {global_cycle}/{n_completed}:  "
              f"SoH={current_soh:.2f}%  SoC={row['SoC_start_pct']:.0f}→"
              f"{row['SoC_end_dis_pct']:.0f}%  WLTPs={wltp_count}  "
              f"T_max={row['T_max_C']:.1f}C")

# =================================================================
# [5/5] Summary variables from PyBaMM (per-cycle)
# =================================================================
print(f"\n  Extracting summary variables...")
sv_rows = []
try:
    sv = sol.summary_variables
    sv_dict = sv.get_summary_variables()
    # sv_dict values are scalars (last cycle) or arrays
    # We need per-cycle, so let's get from each cycle's last state
    # Actually summary_variables accumulates - let's just save the final dict
    for k, v in sorted(sv_dict.items()):
        try:
            sv_rows.append({"variable": k, "value": float(v)})
        except (TypeError, ValueError):
            sv_rows.append({"variable": k, "value": str(v)})
except Exception as e:
    print(f"  Warning: could not extract summary_variables: {e}")

# =================================================================
# Save Excel
# =================================================================
print(f"\n  Saving {xlsx_path}...")
df_m = pd.DataFrame(all_rows)
df_v = pd.concat(all_voltage, ignore_index=True) if all_voltage else pd.DataFrame()
df_sv = pd.DataFrame(sv_rows) if sv_rows else pd.DataFrame()

with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
    df_m.to_excel(writer, sheet_name="Cycles", index=False)

    if not df_v.empty:
        df_v.to_excel(writer, sheet_name="VoltageCurves", index=False)

    if not df_sv.empty:
        df_sv.to_excel(writer, sheet_name="SummaryVars", index=False)

    t_total = time.time() - t_start
    info = [
        ("PyBaMM version", pybamm.__version__),
        ("Model", "SPMe + SEI + Li plating + lumped thermal"),
        ("Parameter set", "OKane2022"),
        ("Cell", "LG M50 (NMC811/Graphite)"),
        ("Capacity [Ah]", CAPACITY_AH),
        ("V nominal [V]", V_NOM),
        ("Pack energy [kWh]", PACK_ENERGY_KWH),
        ("N cells", N_CELLS),
        ("Configuration", f"{N_SERIES}s x {N_PARALLEL}p"),
        ("Pack V nom [V]", round(N_SERIES * V_NOM, 1)),
        ("Pack capacity [Ah]", round(N_PARALLEL * CAPACITY_AH, 1)),
        ("SOC upper [%]", SOC_UPPER_PCT),
        ("SOC lower [%]", SOC_LOWER_PCT),
        ("V upper (OCV) [V]", round(V_UPPER, 4)),
        ("V lower (OCV) [V]", round(V_LOWER, 4)),
        ("Charge current [A]", CHARGE_CURRENT_A),
        ("Charge C-rate", round(CHARGE_CRATE, 3)),
        ("N cycles target", N_CYCLES),
        ("Cycles completed", n_completed),
        ("Status", "COMPLETE" if n_completed >= N_CYCLES else
                   f"PARTIAL ({n_completed}/{N_CYCLES})"),
        ("T ambient [degC]", T_AMBIENT_C),
        ("WLTP duration [s]", round(float(t_raw[-1]), 1)),
        ("WLTP pts original", len(t_raw)),
        ("WLTP pts downsampled", WLTP_POINTS),
        ("WLTPs/discharge (est)", round(n_wltp_est, 2)),
        ("WLTPs/discharge (max)", N_WLTP),
        ("Pack P_max [kW]", round(float(P_raw.max()) / 1000, 2)),
        ("Pack P_min [kW]", round(float(P_raw.min()) / 1000, 2)),
        ("Cell P_max [W]", round(float(P_cell.max()), 3)),
        ("Cell P_min [W]", round(float(P_cell.min()), 3)),
        ("Solve time [s]", round(t_solve, 1)),
        ("Total time [s]", round(t_total, 1)),
        ("Avg time/cycle [s]", round(t_solve / n_completed, 2)),
        ("Initial Q_dis [Ah]",
         round(initial_Q_dis, 5) if initial_Q_dis else ""),
        ("Final SoH [%]",
         round(all_rows[-1]["SoH_pct"], 3) if all_rows else ""),
        ("SoH fade [%]",
         round(all_rows[-1]["SoH_fade_pct"], 4) if all_rows else ""),
    ]
    pd.DataFrame(info, columns=["Parameter", "Value"]).to_excel(
        writer, sheet_name="SimInfo", index=False)
    pd.DataFrame({"SoC": SOC_TABLE, "OCV_V": OCV_TABLE}).to_excel(
        writer, sheet_name="OCV_SoC", index=False)

# Also save CSV backup
df_m.to_csv("pybamm_summary.csv", index=False)

# =================================================================
# Final report
# =================================================================
t_total = time.time() - t_start

print("\n" + "=" * 70)
print("  COMPLETE")
print("=" * 70)
print(f"  Cycles:  {n_completed}/{N_CYCLES}")
print(f"  Solve:   {timedelta(seconds=int(t_solve))}")
print(f"  Total:   {timedelta(seconds=int(t_total))}")
if len(all_rows) > 1:
    s1 = all_rows[0]["SoH_pct"]
    sN = all_rows[-1]["SoH_pct"]
    print(f"  SoH:     {s1:.2f}% -> {sN:.2f}%  (fade {100-sN:.2f}%)")
    print(f"  T_max:   {max(r['T_max_C'] for r in all_rows):.1f} degC")
print(f"  File:    {xlsx_path}")
print("=" * 70)