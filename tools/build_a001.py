"""Circuit Remix Alpha 0.01 (MIT): RH32 without rdiag (no remote diagnostics: no memory reads or card writes over SysEx), under its public name (the
marker A0.01): every function up to RH32 (the Stock+ knob page, pitchmod in DSP core 1)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh32  # noqa: E402

NAME = "A0.01"


def build(name=NAME, **kw):
    return build_rh32.build(name, diag=False, **kw)


if __name__ == "__main__":
    build().finish()
