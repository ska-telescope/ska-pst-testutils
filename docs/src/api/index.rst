.. doctest-skip-all
.. _package-guide:

.. todo::
    - Insert todo's here

*****************
ska_pst_testutils
*****************

The ska_pst_testutils package is a utility Python
module that is to be used only for testing purposes
(i.e. should only be installed as a dev dependency).

The main use of this module the SKA PST project that
has behavioural driven development (BDD) tests. Most
of the code in this package had been ported from the
SKA PST's tests directory so that the code could be
used within Python notebooks or shared with the
SKA PST LMC Python project.

.. toctree::
  :maxdepth: 1

  ska_pst_testutils.analysis<analysis/index>
  ska_pst_testutils.common<common/index>
  ska_pst_testutils.dada<dada/index>
  ska_pst_testutils.dsp<dsp/index>
  ska_pst_testutils.scan_config<scan_config/index>
  ska_pst_testutils.tango<tango/index>
  ska_pst_testutils.udp_gen<udp_gen/index>
