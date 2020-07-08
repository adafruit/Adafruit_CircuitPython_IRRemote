
Introduction
============

.. image:: https://readthedocs.org/projects/adafruit-circuitpython-irremote/badge/?version=latest
    :target: https://circuitpython.readthedocs.io/projects/irremote/en/latest/
    :alt: Documentation Status

.. image :: https://img.shields.io/discord/327254708534116352.svg
    :target: https://adafru.it/discord
    :alt: Discord

.. image:: https://github.com/adafruit/Adafruit_CircuitPython_IRRemote/workflows/Build%20CI/badge.svg
    :target: https://github.com/adafruit/Adafruit_CircuitPython_IRRemote/actions/
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

Installing from PyPI
====================

On supported GNU/Linux systems like the Raspberry Pi, you can install the driver locally `from
PyPI <https://pypi.org/project/adafruit-circuitpython-irremote/>`_. To install for current user:

.. code-block:: shell

    pip3 install adafruit-circuitpython-irremote

To install system-wide (this may be required in some cases):

.. code-block:: shell

    sudo pip3 install adafruit-circuitpython-irremote

To install in a virtual environment in your current project:

.. code-block:: shell

    mkdir project-name && cd project-name
    python3 -m venv .env
    source .env/bin/activate
    pip3 install adafruit-circuitpython-irremote

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


Contributing
============

Contributions are welcome! Please read our `Code of Conduct
<https://github.com/adafruit/Adafruit_CircuitPython_IRRemote/blob/master/CODE_OF_CONDUCT.md>`_
before contributing to help this project stay welcoming.

Documentation
=============

For information on building library documentation, please check out `this guide <https://learn.adafruit.com/creating-and-sharing-a-circuitpython-library/sharing-our-docs-on-readthedocs#sphinx-5-1>`_.
