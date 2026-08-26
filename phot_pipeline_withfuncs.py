
from functions import field_info, action_photometry, plot_lightcurve, concatenate_actions, comp_norm, plot_compnorm_lc, plot_binned_lc
import matplotlib.pyplot as plt 
from astropy.io import fits
from astropy.wcs import WCS
import multiprocessing
from glob import glob 
import pandas as pd
import numpy as np
import argparse
import warnings
import sep 
import os

warnings.filterwarnings("ignore")
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

#creating command line arguments 
# for example will look like this: python phot_pipeline_withfuncs.py NG1019-3345 80120181201055814 -n 4
def parse_args():
 
    parser = argparse.ArgumentParser(
        prog="photometry pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="runs the photometry pipeline for a given NGTS field and campaign.",
    )
 
    positionals = parser.add_argument_group("Positional arguments")
    positionals.add_argument(
        "field_name",
        help="field name",
        type=str,
    )
    positionals.add_argument(
        "campaign_name",
        help="campaign/subdirectory name",
        type=str,
    )
 
    optional = parser.add_argument_group("Optional arguments")
    optional.add_argument(
        "-n",
        "--num-workers",
        help="Number of CPUs to use for parallel photometry.",
        dest="num_workers",
        type=int,
        default=4,
        required=False,
    )
 
    return parser.parse_args()
 
args = parse_args()
 
# specify field and campaign/subdir which is set from the command line instead of hardcoded
field_name = args.field_name
campaign_name = args.campaign_name
 
# setting the number of cores to use 
num_workers = args.num_workers

# get necessary information about field and objects  (list of all actions, source names, and their xy positions)
actions, obj_names, source_id, x, y = field_info(field_name, campaign_name)

# allows for the worker to have just one varyiing argument which is the action and keeps the rest const (fills the other 5 arguments the same each time)
def worker(action):
    return action_photometry(action, source_id=source_id, x=x, y=y, field_name=field_name, campaign_name=campaign_name)

# splits the actions list across num_workers processes which each calls worker(action)
with multiprocessing.Pool(processes=num_workers) as pool:
    pool.map(worker, actions)   # worker is the function called to work on a given action which is given from the list of actions supplied

field_campaign_flux_data = concatenate_actions(actions, field_name, campaign_name)     # returns the dataframe of flux data for the entire field campaign

# plots raw and corrected light curve for each candidate object (visually inspect these to see which ones are actual objects)
for obj in obj_names:
    plot_lightcurve(obj, field_campaign_flux_data, field_name, campaign_name)
    mjd, corrected_flux, corrected_flux_err, disc_mjd = comp_norm(obj, field_name, campaign_name)
    plot_compnorm_lc(mjd, corrected_flux, disc_mjd, obj, field_name, campaign_name)
    plot_binned_lc(mjd, corrected_flux, disc_mjd, obj, field_name, campaign_name)
# could also get this to eventually run over all campaigns present in a field and concatenate them at the end to plot a full field light curve


