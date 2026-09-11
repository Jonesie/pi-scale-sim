# pi-scale-sim

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
- `bin/pi-scale` — control script that runs **on the desktop**, drives the
  Pi-side script over SSH (start/stop/status/restart/log). Symlinked into
  `~/bin/pi-scale` so it's on `PATH`.
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

### Start/stop the desktop-side virtual serial port

Not yet wrapped in a script — currently started manually:

```bash
socat -d -d pty,raw,echo=0,link=$HOME/dev/ttyScale tcp:192.168.51.14:5000 &
```

Find and kill it with:

```bash
pkill -f 'socat.*ttyScale'
```

Once running, any app can read `~/dev/ttyScale` like a normal serial device,
e.g.:

```bash
cat ~/dev/ttyScale
```

## Data file format

One reading per line, plain text. Example (`data/dummy_readings.txt`):

```
ST,GS,+  12.34 kg
ST,GS,+  12.35 kg
```

Line ending sent over the wire defaults to CRLF (`\r\n`), configurable via
`scale_sim.py --line-ending`.
