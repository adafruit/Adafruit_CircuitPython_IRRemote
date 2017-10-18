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

Demo code for upcoming CircuitPlayground Express:

.. code-block: python

    import pulseio
    import board
    import adafruit_irremote

    with pulseio.PulseIn(board.REMOTEIN, maxlen=120, idle_state=True) as p:
        d = adafruit_irremote.GenericDecode()
        code = bytearray(4)
        while True:
            d.decode(p, code)
            print(code)

* Author(s): Scott Shawcroft
"""

import array

class IRDecodeException(Exception):
    pass

class IRNECRepeatException(Exception):
    pass


            
class GenericDecode:
    def bin_data(self, pulses):
        bins = [[pulses[0],0]]
    
        for i in range(len(pulses)):
            p = pulses[i]
            matchedbin = False
            #print(p, end=": ")
            for b in range(len(bins)):
                bin = bins[b]
                if bin[0]*0.75 <= p <= bin[0]*1.25:
                    #print("matches bin")
                    bins[b][0] = (bin[0] + p) // 2  # avg em
                    bins[b][1] += 1                 # track it
                    matchedbin = True
                    break
            if not matchedbin:
                bins.append([p, 1])
            #print(bins)
        return bins

    def decode_bits(self, pulses, debug=False):
        if debug:
            print("length: ", len(pulses))

        # special exception for NEC repeat code!
        if (len(pulses) == 3) and (8000 <= pulses[0] <= 10000) and (2000 <= pulses[1] <= 3000) and (450 <= pulses[2] <= 700):
            raise IRNECRepeatException()

        if len(pulses) < 10:
            raise IRDecodeException("10 pulses minimum")

        # remove any header
        del pulses[0]
        if (len(pulses) % 2):
            del pulses[0]
        if debug:
            print("new length: ", len(pulses))

        evens = pulses[0::2]
        odds = pulses[1::2]
        # bin both halves
        even_bins = self.bin_data(evens)
        odd_bins = self.bin_data(odds)
        if debug: print("evenbins: ", even_bins, "oddbins:", odd_bins)

        outliers = [b[0] for b in (even_bins+odd_bins) if b[1] == 1]
        even_bins = [b for b in even_bins if (b[1] > 1)]
        odd_bins = [b for b in odd_bins if (b[1] > 1)]
        if debug:
            print("evenbins: ", even_bins, "oddbins:", odd_bins, "outliers:", outliers)

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

        if debug:
            print("Pulses:", pulses, "& Bins:", pulse_bins)
        if len(pulse_bins) == 1:
            raise IRDecodeException("Pulses do not differ")
        elif len(pulse_bins) > 2:
            raise IRDecodeException("Only mark & space handled")

        mark = min(pulse_bins[0][0], pulse_bins[1][0])
        space = max(pulse_bins[0][0], pulse_bins[1][0])
        if debug:
            print("Space:",space,"Mark:",mark)

        if outliers:
            pulses = [p for p in pulses if not (outliers[0]*0.75) <= p <= (outliers[0]*1.25)] # skip outliers
        # convert marks/spaces to 0 and 1
        for i in range(len(pulses)):
            if (space*0.75) <= pulses[i] <= (space*1.25):
                pulses[i] = False
            elif (mark*0.75) <= pulses[i] <= (mark*1.25):
                pulses[i] = True
            else:
                raise IRDecodeException("Pulses outside mark/space")
        if debug:
            print(len(pulses), pulses)

        # convert bits to bytes!
        output = [0] * ((len(pulses)+7)//8)
        for i in range(len(pulses)):
            output[i // 8] = output[i // 8] << 1
            if (pulses[i]):
                output[i // 8] |= 1
        return output

    def read_pulses(self, input, max_pulse=10000):
        received = []
        while True:
            while len(input) < 8:   # not too big (slower) or too small (underruns)!
                pass
            while len(input):
                p = input.popleft()
                if p > max_pulse:
                    if not received:
                        continue
                    else:
                        return received
                received.append(p)

class GenericTransmit:
    def __init__(self, header, one, zero, trail):
        self.header = header
        self.one = one
        self.zero = zero
        self.trail = trail

    def transmit(self, pulseout, data):
        durations = array.array('H', [0] * (2 + len(data) * 8 * 2 + 1))
        durations[0] = self.header[0]
        durations[1] = self.header[1]
        durations[-1] = self.trail
        out = 2
        for byte in range(len(data)):
            for i in range(7, -1, -1):
                if (data[byte] & 1 << i) > 0:
                    durations[out] = self.one[0]
                    durations[out + 1] = self.one[1]
                else:
                    durations[out] = self.zero[0]
                    durations[out + 1] = self.zero[1]
                out += 2

        print(durations)
        pulseout.send(durations)
