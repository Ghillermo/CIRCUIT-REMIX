"""Circuit Rhythm 5706 - RH101 (MIT): RH100 + three things from CIRCUIT-HACKS and RH66's sdbulk (the user, 2026-11-14: the plan of RH101,
«do your choices, we'll change the interface later if needed»; docs/PRUEBA_RH101.md lists the choices):
  * OPT osc1x (tools/osc1x.py; sp0 / synthpage / vsel / modmx / projsnd / rpatch): OSC 1's sub-oscillator and noise with one oscillator
    (Hacks' SC52.8): K5 the sub, K6 the noise, K8 LFO -> sub, Shift + K5 / K6 env -> sub / noise, Shift + K8 LFO -> noise (Stock+'s LFO);
    core 0's SUBN at P:$2A37 from sp0's SDS entry (the noise LCG seeded per slot: unison / poly voices decorrelated); one oscillator =
    OSC 2's own knobs at rest (synthpage's c_sydual on the BASE values, never the matrix's offsets; dualext's terms out); the matrix's
    destinations 50-55 (and 32-36) modulated live through c_vsext (c_mxadd), the project (projsnd VA_AT + 9..14), the patch (Hacks' block
    at padding + 142);
  * OPT ingain / setp3b3 (tools/ingain.py, velcurve, setsave): the input's gain +0..+24 dB on Advanced Setup K3, in the stock's own input
    stage on core 0 (asl #4) and the ARM's conversion (Hacks' SC52.6);
  * OPT dupsave (rpatch): Duplicate + an empty slot of the pack's list = saved at once (Hacks' psave), a failed read of either half of a
    bank = its slots foreign, the demos only on forced reads;
  * OPT sdbulk / bulkflag (tools/bulkflag.py, sdyield): no yield in a PCM upload's bulk interval (RH66's fix, without dspgate's dropping)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh100  # noqa: E402
import bulkflag  # noqa: E402
import rhbuild  # noqa: E402

NAME = "RH101"


def build(name=NAME, **kw):
    with rhbuild.options(osc1x=True, ingain=True, setp3b3=True, dupsave=True, sdbulk=True, bulkflag=True):
        b = build_rh100.build(name, **kw)
        b.add("bulkflag", bulkflag)
    return b


if __name__ == "__main__":
    build().finish()
