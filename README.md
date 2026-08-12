# jakackioscar.github.io

My personal site. There are two copies of it. This one lives on GitHub Pages.
The other one is served by a microcontroller I pulled out of a disposable vape.

- <https://jakackioscar.github.io>
- <https://oscarszero.tail35f675.ts.net> — the vape, when it's plugged in

## The vape

The chip is a PY32F030, a Cortex-M0+ with 32 KB of flash and 4 KB of RAM. No
ethernet, no wifi, no serial port hooked up. The only wire going to it is the
debug port, so that's what the web traffic goes through.

A Raspberry Pi Zero bit-bangs SWD on two GPIO pins, no debug probe involved.
OpenOCD handles semihosting, which is basically syscalls for microcontrollers:
the chip hits a breakpoint instruction, the debugger reads its registers, does
the I/O on the host, writes the answer back into a register, and lets it carry
on. Most people use it so `printf` works without a UART. It goes both ways
though, so you can push data in as well as read it out.

That gets you a pipe of bytes. SLIP turns the pipe into packets — it's the
protocol dial-up modems used, and the whole spec is "end each packet with 0xC0,
escape any 0xC0 in the data." A Python script decodes that onto a tun
interface, and from there the Pi's kernel routes to the chip like it's any
other machine on the network. uIP on the chip does TCP and serves the page.

nginx sits in front of all this, because the chip handles one connection at a
time and takes about 12 seconds per page. Through the cache it's 17 ms.

## The part that took two days

None of it worked at first. Packets went out, nothing came back, and OpenOCD
would stop responding to anything at all.

It turned out OpenOCD throws away incoming data on a semihosting connection
unless the chip is *already* sitting in a read:

```c
if (!connection->input_pending) {
    /* consume received data, not for semihosting IO */
    char buf[100];
    int bytes_read = connection_read(connection, buf, buf_len);
```

Which is a completely reasonable thing to do if you're using this as a console.
If someone types while the program isn't reading, that input is junk, so bin
it. It is not reasonable if you're trying to push packets through. Every packet
that arrived while the chip was busy got dropped, and then the chip would go
into a read and block forever waiting for data that had already been deleted.
Since that's a blocking socket read, OpenOCD's whole event loop hung with it,
which is why even telnet went dead.

I patched OpenOCD to hold that data in a 16 KB buffer instead of dropping it,
and to drain the buffer before falling back to a blocking read.

## Why it's slow

`UIP_BUFSIZE` is 384, which puts the TCP MSS at 344 bytes. The page is about
6.6 KB, so that's ~19 segments, and uIP sends one and waits for the ack before
sending the next. Round trip over semihosting is roughly 600 ms. Multiply it
out and you get the 12 seconds.

So it's the number of round trips, not bandwidth. I confirmed that by taking
the SWD clock from 1 MHz to 4 MHz, which made no difference whatsoever and
mostly just made it unstable.

## Credit

The firmware and the original idea are
[BogdanTheGeek's](https://github.com/BogdanTheGeek/semihost-ip). He drove his
chip with pyocd and a real debug probe. Mine runs off bit-banged SWD on a Pi
with OpenOCD, which is how I ended up in the weeds above.

## Working on it

`index.html` is the whole site. One file, no build step, nothing to install.

The vape can't fit the photos or the PDF, so `make-vape-copy.py` strips those
out and writes `vape-index.html`. Run it after changing anything:

```sh
python make-vape-copy.py
```

Then copy that over `lib/uip/fs/index.html~` in the firmware tree, rebuild, and
flash. Skip it and the chip just keeps serving whatever was on it last time,
which is easy to forget about for a while.
