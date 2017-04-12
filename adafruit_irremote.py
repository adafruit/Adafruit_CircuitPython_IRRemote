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

class GenericDecode:
    def decode(self, input, output):
        while True:
            # Wait for input
            print("waiting for more")
            while len(input) < 3:
                pass
            print("not waiting")
            # Find the header
            if input[0] > 7000 and input[0] < 10000 and input[1] > 3000 and input[2] < 2000:
                print("header", input.popleft(), input.popleft(), input[0], len(input))
                break
            else:
                print("skip", input.popleft())

        # The header has started but wait for enough mark/space pairs to make up
        # the bytes we want.
        while len(input) < len(output) * 8 * 2:
            pass

        # Now we're past the header. First, figure out the average space
        mark = input[0]
        space = input[1]
        bits = len(output) * 8
        for i in range(1, bits):
            mark += input[2 * i]
            space += input[2 * i + 1]
        mark /= bits
        space /= bits
        print(mark, space)
        for i in range(len(output)):
            output[i] = 0
        print(output)
        for i in range(bits):
            if i % 8 == 0:
                print()
            output[i // 8] = output[i // 8] << 1
            # TODO(tannewt): Make sure this works if the payload is all 0s or 1s.
            if input[1] > space:
                output[i // 8] |= 1
            print(input.popleft(), input.popleft())
