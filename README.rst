
Introduction
============

.. image:: https://readthedocs.org/projects/adafruit-circuitpython-irremote/badge/?version=latest
    :target: https://circuitpython.readthedocs.io/projects/irremote/en/latest/
    :alt: Documentation Status

.. image :: https://img.shields.io/discord/327254708534116352.svg
    :target: https://discord.gg/nBQh6qu
    :alt: Discord

.. image:: https://travis-ci.com/adafruit/Adafruit_CircuitPython_IRRemote.svg?branch=master
    :target: https://travis-ci.com/adafruit/Adafruit_CircuitPython_IRRemote
    :alt: Build Status

CircuitPython driver for use with IR Receivers.

Examples of products to use this library with:

* `Circuit Playground Express <https://www.adafruit.com/product/3333>`_

* `IR Receiver Sensor <https://www.adafruit.com/product/157>`_

Dependencies
=============
This driver depends on:

* `Adafruit CircuitPython <https://github.com/adafruit/circuitpython>`_

Please ensure all dependencies are available on the CircuitPython filesystem.
This is easily achieved by downloading
`the Adafruit library and driver bundle <https://github.com/adafruit/Adafruit_CircuitPython_Bundle>`_.

Usage Example
=============

.. code-block:: python

    # Circuit Playground Express Demo Code
    # Adjust the pulseio 'board.PIN' if using something else
    import pulseio
    import board
    import adafruit_irremote
    pulsein = pulseio.PulseIn(board.REMOTEIN, maxlen=120, idle_state=True)
    decoder = adafruit_irremote.GenericDecode()

    # size must match what you are decoding! for NEC use 4
    received_code = bytearray(4)

    while True:
        pulses = decoder.read_pulses(pulsein)
        print("Heard", len(pulses), "Pulses:", pulses)
        try:
            code = decoder.decode_bits(pulses, debug=False)
            print("Decoded:", code)
        except adafruit_irremote.IRNECRepeatException:  # unusual short code!
            print("NEC repeat!")
        except adafruit_irremote.IRDecodeException as e:     # failed to decode
            print("Failed to decode: ", e.args)

        print("----------------------------")


Contributing
============

Contributions are welcome! Please read our `Code of Conduct
<https://github.com/adafruit/Adafruit_CircuitPython_IRRemote/blob/master/CODE_OF_CONDUCT.md>`_
before contributing to help this project stay welcoming.

Building locally
================

To build this library locally you'll need to install the
`circuitpython-build-tools <https://github.com/adafruit/circuitpython-build-tools>`_ package.

.. code-block:: shell

    python3 -m venv .env
    source .env/bin/activate
    pip install circuitpython-build-tools

Once installed, make sure you are in the virtual environment:

.. code-block:: shell

    source .env/bin/activate

Then run the build:

.. code-block:: shell

    circuitpython-build-bundles --filename_prefix adafruit-circuitpython-irremote --library_location .

Sphinx documentation
-----------------------

Sphinx is used to build the documentation based on rST files and comments in the code. First,
install dependencies (feel free to reuse the virtual environment from above):

.. code-block:: shell

    python3 -m venv .env
    source .env/bin/activate
    pip install Sphinx sphinx-rtd-theme

Now, once you have the virtual environment activated:

.. code-block:: shell

    cd docs
    sphinx-build -E -W -b html . _build/html

This will output the documentation to ``docs/_build/html``. Open the index.html in your browser to
view them. It will also (due to -W) error out on any warning like Travis will. This is a good way to
locally verify it will pass.
