# -*- coding: utf-8 -*-

"""Adapting the general reegis power plants to the de21 model.

SPDX-FileCopyrightText: 2016-2019 Uwe Krien <krien@uni-bremen.de>

SPDX-License-Identifier: MIT
"""
__copyright__ = "Uwe Krien <krien@uni-bremen.de>"
__license__ = "MIT"


import pandas as pd
import os
import logging
import datetime

from xml.etree import ElementTree

import oemof.tools.logger as logger

from reegis import config as cfg

import berlin_hp.download


def fill_data_gaps(df):
    logging.info('Fill the gaps and resample to hourly values.')
    df.index = pd.DatetimeIndex(
        df.reset_index()['index'].str.slice(0, 19))
    df = df.apply(pd.to_numeric)
    df = df.replace(0, float('nan'))
    for col in df.columns:
        df[col] = df[col].fillna(df[col].shift(7 * 4 * 24))
        df[col] = df[col].interpolate()
        df[col] = df[col].fillna(method='bfill')
    return df


def convert_net_xml2df(year, filename, hourly=True):
    tree = ElementTree.parse(filename)
    elem = tree.getroot()
    logging.info("Convert xml-file to csv-file for {0}".format(year))
    n = 0
    attributes = ['usage', 'generation', 'feed', 'key-acount-usage']
    df = pd.DataFrame(columns=attributes)
    df_temp = pd.DataFrame(columns=attributes)
    for distr_ele in elem.find('district'):
        for f in distr_ele.getchildren():
            value_list = []
            for atr in attributes:
                value_list.append(float(f.find(atr).text))
            df_temp.loc[f.attrib['value'], attributes] = value_list
            if n % 100 == 0:
                df = pd.concat([df, df_temp])
                df_temp = pd.DataFrame(columns=attributes)
            n += 1
    df = pd.concat([df, df_temp])

    # fill the data gaps
    df = fill_data_gaps(df)

    # cut the time series to the given year
    start_date = datetime.datetime(year, 1, 1)
    end_date = datetime.datetime(year + 1, 1, 1)
    df = df.loc[(df.index >= start_date) & (df.index < end_date)]

    # resample to hourly values if hourly is set to True
    if hourly is True:
        df = df.resample('H').mean()
        df = df.interpolate()

    return df


def get_electricity_demand(year, hourly=True, district=None):
    """Get the electricity demand in MW.

    Parameters
    ----------
    year : int
        Year of the data set.
    hourly : bool
        Get hourly data.
    district : str or None
        District of Berlin. If None 'berlin' is used. Possible values are:
        Pankow, Lichtenberg, Marzahn-Hellersdorf, Treptow-Koepenick, Neukoelln,
        Friedrichshain-Kreuzberg, Mitte, Tempelhof-Schöneberg,
        Steglitz-Zehlendorf, Charlottenburg-Wilmersdorf, Reinickendorf, Spandau

    Returns
    -------
    pandas.DataFrame
    """
    if district is None:
        district_name = 'berlin'
    else:
        district_name = district.replace('-', '_')

    xml_filename = os.path.join(
        cfg.get('paths', 'electricity'),
        cfg.get('electricity', 'file_xml').format(year=year,
                                                  district=district_name))
    csv_filename = os.path.join(
        cfg.get('paths', 'electricity'),
        cfg.get('electricity', 'file_csv')).format(year=year,
                                                   district=district_name)

    if not os.path.isfile(xml_filename):
        logging.info("Download {0} grid data for {1} as xml.".format(district,
                                                                     year))
        xml_filename = berlin_hp.download.get_berlin_net_data(
            year, district=district)

    if not os.path.isfile(csv_filename):
        df = convert_net_xml2df(year, xml_filename, hourly=hourly)
        df.to_csv(csv_filename)

    msg = ("The unit for the electricity demand of the source is kW. Values "
           "will be divided by 1000 to get MW.")
    logging.warning(msg)

    return pd.read_csv(csv_filename, index_col=[0], parse_dates=True) / 1000


if __name__ == "__main__":
    logger.define_logging(file_level=logging.INFO)
    d_list = ['berlin', 'Pankow', 'Lichtenberg', 'Marzahn-Hellersdorf',
              'Treptow-Koepenick', 'Neukoelln', 'Friedrichshain-Kreuzberg',
              'Mitte', 'Tempelhof-Schoeneberg', 'Steglitz-Zehlendorf',
              'Charlottenburg-Wilmersdorf', 'Reinickendorf', 'Spandau']
    for district in d_list:
        c = []
        for y in [2012, 2013, 2014, 2015, 2016]:
            d = get_electricity_demand(y, district=district)
            if d.isnull().values.any():
                for column in d.columns:
                    if d[column].isnull().any():
                            c.append(column)
                print(d.loc[d.usage.isnull()])
            if len(c) < 1:
                print("Everything is fine for {0}.".format(district))
            else:
                print(c)
