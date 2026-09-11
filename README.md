# pi-scale-sim

> **Platform note:** the desktop side (`bin/pi-scale`, the socat bridge) is
> only tested on **Linux**. It likely works on **macOS** with little or no
> change (`socat` and pty semantics are the same BSD-derived model), but
> hasn't been verified there. It will **not** work as-is on **Windows** —
> there's no `/dev/pts` pty and no `socat` — you'd need a different bridge
> (e.g. `com0com` for a virtual COM port, or run this under WSL2). The Pi
> side (`scale_sim.py`) is plain Python/TCP and is unaffected by any of this.

Simulates an electronic scale's serial output using a Raspberry Pi, streamed
to a virtual serial port on a desktop over the network — no physical serial
cable required.

## How it works

```
[data file] --> scale_sim.py (Pi, TCP server) --> network --> socat (desktop) --> virtual serial device
```

1. **`scale_sim.py`** runs on the Pi. It reads a text file of readings (one
   per line), and streams them to any connected TCP client at a fixed
   interval, looping forever — like a real scale in continuous-output mode.
2. **`socat`** runs on the desktop and bridges that TCP stream to a local
   pseudo-terminal (`pty`), symlinked at `~/dev/ttyScale`. Any application
   that opens `~/dev/ttyScale` sees exactly what it would from a real serial
   port connected to a real scale.

## Hardware / network setup

- Raspberry Pi: `pitoy` at `192.168.51.14`, SSH alias `pi-scale` (see
  `~/.ssh/config`), login user `pi`, key `~/.ssh/id_ed25519_piscale`.
- No physical serial cable is used — this is a pure network bridge.

## Repo layout

- `scale_sim.py` — the TCP server script that runs **on the Pi**.
- `bin/pi-scale` — control script that runs **on the desktop**. Drives the
  Pi-side script over SSH (`start`/`stop`/`status`/`restart`/`log`), manages
  the local socat bridge (`bridge-start`/`bridge-stop`/`bridge-status`), and
  live-tails the data (`view`). Symlinked into `~/bin/pi-scale` so it's on
  `PATH`.
- `data/dummy_readings.txt` — sample/test data (fake scale readings) used
  for verifying the pipeline end-to-end.

## Usage

### Deploy/update the script on the Pi

```bash
scp scale_sim.py pi-scale:~/scale_sim.py
```

### Control the simulator from the desktop

```bash
pi-scale start      # start streaming on the Pi
pi-scale stop       # stop it
pi-scale restart
pi-scale status
pi-scale log         # tail the Pi-side log
```

Override the data file, port, or interval per-run:

```bash
SCALE_DATA=~/mydata.txt SCALE_PORT=5000 SCALE_INTERVAL=0.5 pi-scale start
```

To use a real data file, copy it to the Pi first:

```bash
scp mydata.txt pi-scale:~/mydata.txt
SCALE_DATA=~/mydata.txt pi-scale start
```

### Desktop-side virtual serial port (the socat bridge)

Also managed by `pi-scale`:

```bash
pi-scale bridge-start    # start the socat bridge -> ~/dev/ttyScale
pi-scale bridge-stop
pi-scale bridge-status
```

The bridge process is fully detached (via `setsid`) so it keeps running
independently of whatever shell or script started it.

### View the live serial data

```bash
pi-scale view
```

Starts the bridge if it isn't already running, then prints each incoming
reading with a timestamp:

```
10:43:11  ST,GS,+  12.34 kg
10:43:12  ST,GS,+  12.35 kg
```

`Ctrl-C` stops viewing but leaves the bridge running for other consumers.
You can also read `~/dev/ttyScale` directly with any tool that treats it as
a serial device, e.g. `cat ~/dev/ttyScale` or a Python `pyserial` script.

## Serial settings

`~/dev/ttyScale` is a **pty** (pseudo-terminal), not real UART hardware. That
matters for two reasons:

- socat can still *set* the standard termios line settings on it (baud, data
  bits, parity, stop bits) — an app that calls `tcgetattr()`/`stty` on the
  device will see the values below, and some apps refuse to open a serial
  port unless it reports settings they expect.
- But a pty doesn't actually enforce timing electrically the way a real UART
  does. Nothing here will throttle bytes to genuinely take "1/9600th of a
  second per bit" — the effective pacing of the data is controlled entirely
  by `scale_sim.py --interval` on the Pi (how often a line is sent), not by
  the baud rate.

| Setting     | Default | Env var           | Values          |
|-------------|---------|--------------------|-----------------|
| Baud rate   | 9600    | `SCALE_BAUD`       | any integer, e.g. `1200`, `9600`, `19200`, `115200` |
| Data bits   | 8       | `SCALE_DATABITS`   | `5`, `6`, `7`, `8` |
| Parity      | none    | `SCALE_PARITY`     | `none`, `even`, `odd` |
| Stop bits   | 1       | `SCALE_STOPBITS`   | `1`, `2` |

9600 8N1 is the default because it's the most common setting for RS232
scale/indicator protocols, but override any of these when starting the
bridge:

```bash
SCALE_BAUD=19200 SCALE_PARITY=even SCALE_STOPBITS=2 pi-scale bridge-start
```

Restart the bridge (`pi-scale bridge-stop && pi-scale bridge-start`) for a
settings change to take effect — they're applied at bridge start, not live.

Verify what's currently applied with:

```bash
stty -F ~/dev/ttyScale -a
```

To change the **data rate** (readings per second) rather than the serial
line's advertised baud rate, use `SCALE_INTERVAL` on the Pi-side `start`
command instead — see [Control the simulator from the
desktop](#control-the-simulator-from-the-desktop) above.

## Data file format

One reading per line, plain text. Example (`data/dummy_readings.txt`):

```
ST,GS,+  12.34 kg
ST,GS,+  12.35 kg
```

Line ending sent over the wire defaults to CRLF (`\r\n`), configurable via
`scale_sim.py --line-ending`.
