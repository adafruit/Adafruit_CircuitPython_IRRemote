# The MIT License (MIT)
#
# Copyright (c) 2017 Scott Shawcroft for Adafruit Industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
`adafruit_irremote`
====================================================

Demo code for Circuit Playground Express:

.. code-block:: python

    # Circuit Playground Express Demo Code
    # Adjust the pulseio 'board.PIN' if using something else
    import pulseio
    import board
    import adafruit_irremote

    pulsein = pulseio.PulseIn(board.REMOTEIN, maxlen=120, idle_state=True)
    decoder = adafruit_irremote.GenericDecode()


    while True:
        pulses = decoder.read_pulses(pulsein)
        print("Heard", len(pulses), "Pulses:", pulses)
        try:
            code = decoder.decode_bits(pulses)
            print("Decoded:", code)
        except adafruit_irremote.IRNECRepeatException:  # unusual short code!
            print("NEC repeat!")
        except adafruit_irremote.IRDecodeException as e:     # failed to decode
            print("Failed to decode: ", e.args)

        print("----------------------------")

* Author(s): Scott Shawcroft

Implementation Notes
--------------------

**Hardware:**

* `CircuitPlayground Express <https://www.adafruit.com/product/3333>`_

* `IR Receiver Sensor <https://www.adafruit.com/product/157>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the ESP8622 and M0-based boards:
  https://github.com/adafruit/circuitpython/releases

"""

# Pretend self matter because we may add object level config later.
# pylint: disable=no-self-use

import array
import time

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_IRRemote.git"


class IRDecodeException(Exception):
    """Generic decode exception"""


class IRNECRepeatException(Exception):
    """Exception when a NEC repeat is decoded"""


def _bits_to_value_lsb(bits):
    result = 0

    for position, value in enumerate(bits):
        result += value << position

    return result


class GenericDecode:
    """Generic decoding of infrared signals"""

    def bin_data(self, pulses):
        """Compute bins of pulse lengths where pulses are +-25% of the average.

           :param list pulses: Input pulse lengths
           """
        bins = [[pulses[0], 0]]

        for _, pulse in enumerate(pulses):
            matchedbin = False
            # print(pulse, end=": ")
            for b, pulse_bin in enumerate(bins):
                if pulse_bin[0] * 0.75 <= pulse <= pulse_bin[0] * 1.25:
                    # print("matches bin")
                    bins[b][0] = (pulse_bin[0] + pulse) // 2  # avg em
                    bins[b][1] += 1  # track it
                    matchedbin = True
                    break
            if not matchedbin:
                bins.append([pulse, 1])
            # print(bins)
        return bins

    def decode_sirc(self, pulses):
        """Decode SIRC (Sony) protocol commands from raw pulses.

        The Sony command protocol uses a different format than the normal RC-5,
        which requires a different decoding scheme.

        Details of the protocol can be found at:

        https://www.sbprojects.net/knowledge/ir/sirc.php
        http://www.righto.com/2010/03/understanding-sony-ir-remote-codes-lirc.html
        """

        # SIRC supports 12-, 15- and 20-bit commands. There's always one header pulse,
        # and then two pulses per bit, so accept 25-, 31- and 41-pulses commands.
        if not len(pulses) in [25, 31, 41]:
            raise IRDecodeException("Invalid number of pulses %d" % len(pulses))

        if not 2200 <= pulses[0] <= 2600:
            raise IRDecodeException("Invalid header pulse length (%d usec)" % pulses[0])

        evens = pulses[1::2]
        odds = pulses[2::2]
        pairs = zip(evens, odds)
        bits = []
        for even, odd in pairs:
            if odd > even * 1.75:
                bits.append(1)
            else:
                bits.append(0)

        command_bits = bits[0:7]

        # 20-bit commands are the same as 12-bit but with an additional 8-bit
        # extension. 15-bit commands use 8-bit for the device address instead.
        if len(pulses) == 31:
            device_bits = bits[7:15]
            extended_bits = None
        else:
            device_bits = bits[7:12]
            extended_bits = bits[12:]

        command = _bits_to_value_lsb(command_bits)
        device = _bits_to_value_lsb(device_bits)
        if extended_bits:
            extended = _bits_to_value_lsb(extended_bits)
        else:
            extended = None

        if extended is None:
            return [command, device]

        return [command, device, extended]

    def decode_bits(self, pulses):
        """Decode the pulses into bits."""
        # pylint: disable=too-many-branches,too-many-statements

        # special exception for NEC repeat code!
        if (
            (len(pulses) == 3)
            and (8000 <= pulses[0] <= 10000)
            and (2000 <= pulses[1] <= 3000)
            and (450 <= pulses[2] <= 700)
        ):
            raise IRNECRepeatException()

        if len(pulses) < 10:
            raise IRDecodeException("10 pulses minimum")

        # Ignore any header (evens start at 1), and any trailer.
        if len(pulses) % 2 == 0:
            pulses_end = -1
        else:
            pulses_end = None

        evens = pulses[1:pulses_end:2]
        odds = pulses[2:pulses_end:2]

        # bin both halves
        even_bins = self.bin_data(evens)
        odd_bins = self.bin_data(odds)

        outliers = [b[0] for b in (even_bins + odd_bins) if b[1] == 1]
        even_bins = [b for b in even_bins if b[1] > 1]
        odd_bins = [b for b in odd_bins if b[1] > 1]

        if not even_bins or not odd_bins:
            raise IRDecodeException("Not enough data")

        if len(even_bins) == 1:
            pulses = odds
            pulse_bins = odd_bins
        elif len(odd_bins) == 1:
            pulses = evens
            pulse_bins = even_bins
        else:
            raise IRDecodeException("Both even/odd pulses differ")

        if len(pulse_bins) == 1:
            raise IRDecodeException("Pulses do not differ")
        if len(pulse_bins) > 2:
            raise IRDecodeException("Only mark & space handled")

        mark = min(pulse_bins[0][0], pulse_bins[1][0])
        space = max(pulse_bins[0][0], pulse_bins[1][0])

        if outliers:
            # skip outliers
            pulses = [
                p
                for p in pulses
                if not (outliers[0] * 0.75) <= p <= (outliers[0] * 1.25)
            ]
        # convert marks/spaces to 0 and 1
        for i, pulse_length in enumerate(pulses):
            if (space * 0.75) <= pulse_length <= (space * 1.25):
                pulses[i] = False
            elif (mark * 0.75) <= pulse_length <= (mark * 1.25):
                pulses[i] = True
            else:
                raise IRDecodeException("Pulses outside mark/space")

        # convert bits to bytes!
        output = [0] * ((len(pulses) + 7) // 8)
        for i, pulse_length in enumerate(pulses):
            output[i // 8] = output[i // 8] << 1
            if pulse_length:
                output[i // 8] |= 1
        return output

    def _read_pulses_non_blocking(
        self, input_pulses, max_pulse=10000, pulse_window=0.10
    ):
        """Read out a burst of pulses without blocking until pulses stop for a specified
            period (pulse_window), pruning pulses after a pulse longer than ``max_pulse``.

            :param ~pulseio.PulseIn input_pulses: Object to read pulses from
            :param int max_pulse: Pulse duration to end a burst
            :param float pulse_window: pulses are collected for this period of time
           """
        received = None
        recent_count = 0
        pruning = False
        while True:
            while input_pulses:
                pulse = input_pulses.popleft()
                recent_count += 1
                if pulse > max_pulse:
                    if received is None:
                        continue
                    pruning = True
                if not pruning:
                    if received is None:
                        received = []
                    received.append(pulse)

            if recent_count == 0:
                return received
            recent_count = 0
            time.sleep(pulse_window)

    def read_pulses(
        self,
        input_pulses,
        *,
        max_pulse=10000,
        blocking=True,
        pulse_window=0.10,
        blocking_delay=0.10
    ):
        """Read out a burst of pulses until pulses stop for a specified
            period (pulse_window), pruning pulses after a pulse longer than ``max_pulse``.

            :param ~pulseio.PulseIn input_pulses: Object to read pulses from
            :param int max_pulse: Pulse duration to end a burst
            :param bool blocking: If True, will block until pulses found.
                If False, will return None if no pulses.
                Defaults to True for backwards compatibility
            :param float pulse_window: pulses are collected for this period of time
            :param float blocking_delay: delay between pulse checks when blocking
           """
        while True:
            pulses = self._read_pulses_non_blocking(
                input_pulses, max_pulse, pulse_window
            )
            if blocking and pulses is None:
                time.sleep(blocking_delay)
                continue
            return pulses


class GenericTransmit:
    """Generic infrared transmit class that handles encoding."""

    def __init__(self, header, one, zero, trail):
        self.header = header
        self.one = one
        self.zero = zero
        self.trail = trail

    def transmit(self, pulseout, data):
        """Transmit the ``data`` using the ``pulseout``.

           :param pulseio.PulseOut pulseout: PulseOut to transmit on
           :param bytearray data: Data to transmit
           """
        durations = array.array("H", [0] * (2 + len(data) * 8 * 2 + 1))
        durations[0] = self.header[0]
        durations[1] = self.header[1]
        durations[-1] = self.trail
        out = 2
        for byte_index, _ in enumerate(data):
            for i in range(7, -1, -1):
                if (data[byte_index] & 1 << i) > 0:
                    durations[out] = self.one[0]
                    durations[out + 1] = self.one[1]
                else:
                    durations[out] = self.zero[0]
                    durations[out + 1] = self.zero[1]
                out += 2

        # print(durations)
        pulseout.send(durations)
