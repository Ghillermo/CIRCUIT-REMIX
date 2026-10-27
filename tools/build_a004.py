"""Circuit Remix Alpha 0.04 (MIT): RH50 without rdiag (no remote diagnostics: no memory reads or card writes over SysEx), under its public name
(the marker A0.04): Alpha 0.03's functions plus RH37-RH50 (loop scan, K8 at the tempo, the granular on up to 4 tracks with its page and
filter, stereo Sample Rec, the playback start, cue, line input, the stereo link, the Tracks' pending functions).  Experimental."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_rh50  # noqa: E402

NAME = "A0.04"


def build(name=NAME, **kw):
    return build_rh50.build(name, diag=False, **kw)


if __name__ == "__main__":
    build().finish()
