# SPDX-FileCopyrightText: 2017 Scott Shawcroft for Adafruit Industries
#
# SPDX-License-Identifier: MIT

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
import array
from collections import namedtuple
import time

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_IRRemote.git"


class IRDecodeException(Exception):
    """Generic decode exception"""


class IRNECRepeatException(Exception):
    """Exception when a NEC repeat is decoded"""


def bin_data(pulses):
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


def decode_bits(pulses):
    """Decode the pulses into bits."""
    # pylint: disable=too-many-branches,too-many-statements

    # TODO The name pulses is redefined several times below, so we'll stash the
    # original in a separate variable for now. It might be worth refactoring to
    # avoid redefining pulses, for the sake of readability.
    input_pulses = tuple(pulses)
    pulses = list(pulses)  # Copy to avoid mutating input.

    # special exception for NEC repeat code!
    if (
        (len(pulses) == 3)
        and (8000 <= pulses[0] <= 10000)
        and (2000 <= pulses[1] <= 3000)
        and (450 <= pulses[2] <= 700)
    ):
        return NECRepeatIRMessage(input_pulses)

    if len(pulses) < 10:
        msg = UnparseableIRMessage(input_pulses, reason="Too short")
        raise FailedToDecode(msg)

    # Ignore any header (evens start at 1), and any trailer.
    if len(pulses) % 2 == 0:
        pulses_end = -1
    else:
        pulses_end = None

    evens = pulses[1:pulses_end:2]
    odds = pulses[2:pulses_end:2]

    # bin both halves
    even_bins = bin_data(evens)
    odd_bins = bin_data(odds)

    outliers = [b[0] for b in (even_bins + odd_bins) if b[1] == 1]
    even_bins = [b for b in even_bins if b[1] > 1]
    odd_bins = [b for b in odd_bins if b[1] > 1]

    if not even_bins or not odd_bins:
        msg = UnparseableIRMessage(input_pulses, reason="Not enough data")
        raise FailedToDecode(msg)

    if len(even_bins) == 1:
        pulses = odds
        pulse_bins = odd_bins
    elif len(odd_bins) == 1:
        pulses = evens
        pulse_bins = even_bins
    else:
        msg = UnparseableIRMessage(input_pulses, reason="Both even/odd pulses differ")
        raise FailedToDecode(msg)

    if len(pulse_bins) == 1:
        msg = UnparseableIRMessage(input_pulses, reason="Pulses do not differ")
        raise FailedToDecode(msg)
    if len(pulse_bins) > 2:
        msg = UnparseableIRMessage(input_pulses, reason="Only mark & space handled")
        raise FailedToDecode(msg)

    mark = min(pulse_bins[0][0], pulse_bins[1][0])
    space = max(pulse_bins[0][0], pulse_bins[1][0])

    if outliers:
        # skip outliers
        pulses = [
            p for p in pulses if not (outliers[0] * 0.75) <= p <= (outliers[0] * 1.25)
        ]
    # convert marks/spaces to 0 and 1
    for i, pulse_length in enumerate(pulses):
        if (space * 0.75) <= pulse_length <= (space * 1.25):
            pulses[i] = False
        elif (mark * 0.75) <= pulse_length <= (mark * 1.25):
            pulses[i] = True
        else:
            msg = UnparseableIRMessage(input_pulses, reason="Pulses outside mark/space")
            raise FailedToDecode(msg)

    # convert bits to bytes!
    output = [0] * ((len(pulses) + 7) // 8)
    for i, pulse_length in enumerate(pulses):
        output[i // 8] = output[i // 8] << 1
        if pulse_length:
            output[i // 8] |= 1
    return IRMessage(tuple(input_pulses), code=tuple(output))


IRMessage = namedtuple("IRMessage", ("pulses", "code"))
"Pulses and the code they were parsed into"

UnparseableIRMessage = namedtuple("IRMessage", ("pulses", "reason"))
"Pulses and the reason that they could not be parsed into a code"

NECRepeatIRMessage = namedtuple("NECRepeatIRMessage", ("pulses",))
"Pulses interpreted as an NEC repeat code"


class FailedToDecode(Exception):
    "Raised by decode_bits. Error argument is UnparseableIRMessage"


class NonblockingGenericDecode:
    """
    Decode pulses into bytes in a non-blocking fashion.

    :param ~pulseio.PulseIn input_pulses: Object to read pulses from
    :param int max_pulse: Pulse duration to end a burst.  Units are microseconds.

    >>> pulses = PulseIn(...)
    >>> decoder = NonblockingGenericDecoder(pulses)
    >>> for message in decoder.read():
    ...     if isinstace(message, IRMessage):
    ...         message.code  # TA-DA! Do something with this in your application.
    ...     else:
    ...         # message is either NECRepeatIRMessage or
    ...         # UnparseableIRMessage. You may decide to ignore it, raise
    ...         # an error, or log the issue to a file. If you raise or log,
    ...         # it may be helpful to include message.pulses in the error message.
    ...         ...
    """

    def __init__(self, pulses, max_pulse=10_000):
        self.pulses = pulses  # PulseIn
        self.max_pulse = max_pulse
        self._unparsed_pulses = []  # internal buffer of partial messages

    def read(self):
        """
        Consume all pulses from PulseIn. Yield decoded messages, if any.

        If a partial message is received, this does not block to wait for the
        rest. It stashes the partial message, to be continued the next time it
        is called.
        """
        # Consume from PulseIn.
        while self.pulses:
            pulse = self.pulses.popleft()
            self._unparsed_pulses.append(pulse)
            if pulse > self.max_pulse:
                # End of message! Decode it and yield a BaseIRMessage.
                try:
                    yield decode_bits(self._unparsed_pulses)
                except FailedToDecode as err:
                    # If you want to debug failed decodes, this would be a good
                    # place to print/log or (re-)raise.
                    (unparseable_message,) = err.args
                    yield unparseable_message
                self._unparsed_pulses.clear()
                # TODO Do we need to consume and throw away more pulses here?
                # I'm unclear about the role that "pruning" plays in the
                # original implementation in GenericDecode._read_pulses_non_blocking.
        # When we reach here, we have consumed everything from PulseIn.
        # If there are some pulses in self._unparsed_pulses, they represent
        # partial messages. We'll finish them next time read() is called.


class GenericDecode:
    """Generic decoding of infrared signals"""

    # Note: pylint's complaint about the following three methods (no self-use)
    # is absolutely correct, which is why the code was refactored, but we need
    # this here for back-compat, hence we disable pylint for that specific
    # complaint.

    def bin_data(self, pulses):  # pylint: disable=no-self-use
        "Wraps the top-level function bin_data for backward-compatibility."
        return bin_data(pulses)

    def decode_bits(self, pulses):  # pylint: disable=no-self-use
        "Wraps the top-level function decode_bits for backward-compatibility."
        result = decode_bits(pulses)
        if isinstance(result, NECRepeatIRMessage):
            raise IRNECRepeatException()
        if isinstance(result, UnparseableIRMessage):
            raise IRDecodeException("10 pulses minimum")
        return result.code

    def _read_pulses_non_blocking(
        self, input_pulses, max_pulse=10000, pulse_window=0.10
    ):  # pylint: disable=no-self-use
        """Read out a burst of pulses without blocking until pulses stop for a specified
        period (pulse_window), pruning pulses after a pulse longer than ``max_pulse``.

        :param ~pulseio.PulseIn input_pulses: Object to read pulses from
        :param int max_pulse: Pulse duration to end a burst
        :param float pulse_window: pulses are collected for this period of time
        """
        # Note: pylint's complaint (no self-use) is absolutely correct, which
        # is why the code was refactored, but we need this here for
        # back-compat, hence we disable pylint.
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
        blocking_delay=0.10,
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
    """Generic infrared transmit class that handles encoding.

    :param int header: The length of header in microseconds
    :param int one: The length of a one in microseconds
    :param int zero: The length of a zero in microseconds
    :param int trail: The length of the trail in microseconds, set to None to disable
    :param bool debug: Enable debug output, default False
    """

    def __init__(self, header, one, zero, trail, *, debug=False):
        self.header = header
        self.one = one
        self.zero = zero
        self.trail = trail
        self.debug = debug

    def transmit(self, pulseout, data, *, repeat=0, delay=0, nbits=None):
        """Transmit the ``data`` using the ``pulseout``.

        :param pulseio.PulseOut pulseout: PulseOut to transmit on
        :param bytearray data: Data to transmit
        :param int repeat: Number of additional retransmissions of the data, default 0
        :param float delay: Delay between any retransmissions, default 0
        :param int nbits: Optional number of bits to send,
            useful to send fewer bits than in the data bytes
        """
        bits_to_send = len(data) * 8
        if nbits is not None and nbits < bits_to_send:
            bits_to_send = nbits

        durations = array.array(
            "H", [0] * (2 + bits_to_send * 2 + (0 if self.trail is None else 1))
        )

        durations[0] = self.header[0]
        durations[1] = self.header[1]
        if self.trail is not None:
            durations[-1] = self.trail
        out = 2
        bit_count = 0
        for byte_index, _ in enumerate(data):
            for i in range(7, -1, -1):
                if (data[byte_index] & 1 << i) > 0:
                    durations[out] = self.one[0]
                    durations[out + 1] = self.one[1]
                else:
                    durations[out] = self.zero[0]
                    durations[out + 1] = self.zero[1]
                out += 2
                bit_count += 1
                if bit_count >= bits_to_send:
                    break

        if self.debug:
            print(durations)

        pulseout.send(durations)
        for _ in range(repeat):
            if delay:
                time.sleep(delay)
            pulseout.send(durations)
