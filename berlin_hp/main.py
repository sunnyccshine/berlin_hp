# -*- coding: utf-8 -*-

"""Main script.

SPDX-FileCopyrightText: 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


# Python libraries
import os
import logging
from datetime import datetime
import time
import traceback

# oemof packages
from oemof.tools import logger

# internal modules
import reegis as cfg
import berlin_hp


def stopwatch():
    if not hasattr(stopwatch, 'start'):
        stopwatch.start = datetime.now()
    return str(datetime.now() - stopwatch.start)[:-7]


def main(year):
    stopwatch()

    sc = berlin_hp.Scenario(name='berlin_hp', year=year, debug=False)

    path = os.path.join(cfg.get('paths', 'scenario'), 'berlin_hp', str(year))

    logging.info("Read scenario from excel-sheet: {0}".format(stopwatch()))
    excel_fn = os.path.join(
        path, '_'.join(['berlin_hp', str(year), 'single']) + '.xls')

    if not os.path.isfile(excel_fn):
        berlin_hp.basic_scenario.create_basic_scenario(year)

    sc.load_excel(excel_fn)
    sc.check_table('time_series')

    logging.info("Add nodes to the EnergySystem: {0}".format(stopwatch()))
    sc.add_nodes2solph()

    # Save energySystem to '.graphml' file.
    sc.plot_nodes(filename=os.path.join(path, 'berlin_hp'),
                  remove_nodes_with_substrings=['bus_cs'])

    logging.info("Create the concrete model: {0}".format(stopwatch()))
    sc.create_model()

    logging.info("Solve the optimisation model: {0}".format(stopwatch()))
    sc.solve()

    logging.info("Solved. Dump results: {0}".format(stopwatch()))
    sc.dump_es(os.path.join(path, 'berlin_hp_{0}_single.esys'.format(
        str(year))))

    logging.info("All done. berlin_hp finished without errors: {0}".format(
        stopwatch()))


if __name__ == "__main__":
    logger.define_logging()
    for y in [2014]:
        try:
            main(y)
        except Exception as e:
            logging.error(traceback.format_exc())
            time.sleep(0.5)
            logging.error(e)
            time.sleep(0.5)
