# jakackioscar.github.io

Source for my personal site.

There are two copies of it. This one is served by GitHub Pages. The other is
served by a microcontroller I pulled out of a disposable vape.

**Live:**
- <https://jakackioscar.github.io> — this copy
- <https://oscarszero.tail35f675.ts.net> — the vape, when it's plugged in

---

## The vape

The chip is a **PY32F030**, a Cortex-M0+ with 32 KB of flash and 4 KB of RAM,
salvaged from a disposable vape. It has no Ethernet, no WiFi, and no UART
wired up. The only connection to it is the debug port, so that's what carries
the IP traffic.

**How the traffic gets in and out:**

1. A Raspberry Pi Zero W bit-bangs **SWD** on two GPIO pins — no debug probe
2. **Semihosting** turns the debug connection into a byte pipe. The chip
   executes a breakpoint instruction, OpenOCD reads its registers, performs
   the I/O on the host, writes the result back, and resumes it
3. **SLIP** frames those bytes into IP packets — the same protocol dial-up
   modems used
4. A Python bridge decodes SLIP onto a **tun0** interface, so the Pi's kernel
   can route to the chip like any other host
5. **uIP** on the chip handles TCP/IP and serves the page

**nginx caches the result.** The chip serves one connection at a time and takes
about 12 seconds per page, so exposing it directly would be a bad idea. Cached
responses come back in ~17 ms, and the chip only gets hit when the cache
expires.

### The bug

It didn't work at first. OpenOCD's semihosting-over-TCP was discarding all
inbound data whenever the target wasn't *already* blocked in a `SYS_READ`:

```c
if (!connection->input_pending) {
    /* consume received data, not for semihosting IO */
    char buf[100];
    int bytes_read = connection_read(connection, buf, buf_len);
```

That's a fair assumption for an interactive console, where input arriving while
nothing is reading really is junk. It's fatal for a packet stream — every
packet sent while the chip was executing got binned, and the chip then blocked
forever waiting for data that no longer existed.

I patched OpenOCD to buffer that data instead of dropping it: the input handler
appends to a 16 KB ring, and `semihosting_redirect_read()` drains that buffer
before falling back to a blocking socket read.

### Why it's slow

`UIP_BUFSIZE` is 384 bytes, so the TCP MSS is 344. A 6.6 KB page is roughly 19
segments, uIP is stop-and-wait, and the round-trip time over semihosting is
~600 ms. It's bound by the number of round trips, not by bandwidth — raising
the SWD clock from 1 MHz to 4 MHz changed the page load time by nothing.

### Credit

The original idea and the `semihost-ip` firmware are
[BogdanTheGeek's](https://github.com/BogdanTheGeek/semihost-ip). His version
drives the chip with pyocd and a hardware debug probe. Mine runs on
bit-banged SWD from a Pi Zero with OpenOCD, which is what turned up the bug
above.

---

## Files

| | |
|---|---|
| `index.html` | The site. Single file, no build step, no dependencies. |
| `make-vape-copy.py` | Generates the vape's copy from `index.html`. |
| `vape-index.html` | That generated copy. Photos and the PDF stripped out. |
| `resume.pdf`, `me.jpg`, `vape.jpg` | Assets. The page degrades gracefully without them. |

## Updating

Edit `index.html`, then push. GitHub Pages picks it up in a minute or so.

To update the vape as well:

```sh
python make-vape-copy.py
```

Then copy `vape-index.html` to `lib/uip/fs/index.html~` in the firmware tree,
rebuild, and reflash. Without that step the two copies drift apart, and the
chip keeps serving whatever was last written to it.
