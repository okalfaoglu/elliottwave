import os
import sys
import signal
import faulthandler

def enable() -> None:
    flag = os.getenv("EW6_STACKDUMP", "1").lower()
    if flag in ("0", "false", "no", "off"):
        return

    try:
        faulthandler.register(signal.SIGUSR1, all_threads=True, chain=False)
        if os.getenv("EW6_STACKDUMP_VERBOSE", "0").lower() in ("1", "true", "yes", "on"):
            print("[EW6] SIGUSR1 stackdump REGISTERED", file=sys.stderr)
    except Exception as e:
        print(f"[EW6] SIGUSR1 stackdump FAILED: {e!r}", file=sys.stderr)
