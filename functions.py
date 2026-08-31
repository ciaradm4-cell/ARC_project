import numpy as np
import sep 
import matplotlib.pyplot as plt 
import pandas as pd
import os
from astropy.io import fits
from astropy.wcs import WCS
from glob import glob 
import warnings
warnings.filterwarnings("ignore")
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
 

# takes field name and campaign/subdirectory name and outputs the list of actions in there and the names and (x,y) coords of all the objects to do photometry on 
def field_info(field_name, campaign_name):

    with fits.open(f'field_info/{field_name}/{campaign_name}/{field_name}_AG{campaign_name}_WCS.fits', relax=True) as hdul: # open the file and using relax=True like advised to 

        hdul.info()  
        print(repr(hdul[0].header))     # printing all the info in the header 
        header = hdul[0].header

    w = WCS(header, relax=True)   # WCS transformation that we will apply to the rest 

    # load in all relevant files 
    actions = glob(f'images/{field_name}/{campaign_name}/action*/', recursive=True)    # list of all actions - PRINT THIS AND CHECK
    df_fields_obs = pd.read_csv('fields_and_observing_times_corrected.csv')    # crossmatch file
    df_comp = pd.read_csv(f'field_info/{field_name}/{field_name}_discmag_comparison_stars.csv')    # the comparison stars file for this campaign/subdirectory

    # on a per field basis, picking out the field of the campaign and extracting the ra and decs aswell as names of the objects that could be observed 
    candidates = df_fields_obs[(df_fields_obs['field_name'] == field_name)]
    obj_names = candidates['obj_name']
    ra = candidates['obj_ra (deg)']
    dec = candidates['obj_dec (deg)']

    # appending the ra and decs of the comparison stars to these candidate objects so that the photometry runs over these also
    ra = np.append(ra, df_comp['ra'])
    dec = np.append(dec, df_comp['dec'])
    source_id = np.append(obj_names, df_comp['source_id'])      # storing all their names (obj names then gaia source ids)
    
    # WCS
    x, y = w.all_world2pix(ra, dec, 0)      # converting to x and y (0 sets origin)
    x-=20      #to fix offset introduced by bias 

    return actions, obj_names, source_id, x, y      # outputs x and y arrays for all objects and also a list of actions for the field



# for action in actions:
def action_photometry(action, source_id, x, y, field_name, campaign_name):     # this acts on a single action to run photometry on all sources in the field

    n_frames = 6    # sets stacking 
    action_id = int(action.split('/')[-2].split('_')[0].replace('action', ''))      # extracts action id from file name
    
    # cutting the first 30 frames from each action while camera settles 
    files = np.array(os.listdir(action))
    files = files[30:]
    r = files.shape[0]%n_frames
    #files = files[:-1*r]  # this was going to give 0s if there is no remainder? I think? since it would be files[:-1*0]=files[:0]

    if r:                                  # only trim if there's an actual leftover
        files = files[:-r]

    # reshaping the files so that we can properly bin them
    new_shape = [int(files.shape[0]/n_frames), n_frames]
    files = files.reshape(new_shape)

    # need to check how this works within a function...
    obj_flux = [] 
    obj_flux_err = []
    obj_time = []

    for i in range(files.shape[0]):     # for each stack, runs this loop

        mjd = np.zeros(n_frames)    # mjd of stack is the median of the timestamps of the stack

        for j in range(n_frames):
            first = 0 

            #for every 6 frames, call each image, do bias subtraction, and add them together

            try:
                with fits.open(os.path.join(action, files[i, j])) as hdul: 
                    frame = hdul[0].data.astype(np.float64)
                    header = hdul[0].header
                mjd[j] = header['MJD']

        
                bias_value = np.median(frame[:, 2075:], axis=1)  
                frame = frame[:, 20:2068] - bias_value 

                if j == first:
                    frame_stack = frame
                else:
                    frame_stack += frame

            except Exception as e:
                print(f'failed to open fits file {action, files[i, j]}')
                print(f'Error: {e}')
                if j == first:
                    first+=1
                continue

        
        bkg = sep.Background(frame_stack)   # calculates the background noise on the stack
        data_sub = frame_stack - bkg    # subtracts the background from the stack

        # circular aperture photometry about the obj coords including all potential objects and al comparison stars
        flux, fluxerr, flag = sep.sum_circle(data_sub, x, y, 3, err=bkg.globalrms, gain=1.0)      # 3 pixel radius about each object

        # each row is a different minute binned stamp
        row = pd.DataFrame({'action_id': [action_id], 'MJD': [np.median(mjd)]})
        for i in range(len(source_id)):

            row[f'{source_id[i]}_flux'] = flux[i]
            row[f'{source_id[i]}_flux_err'] = fluxerr[i]
            row[f'{source_id[i]}_flag'] = flag[i]

        results_dir = f'test_results/{field_name}/{campaign_name}'
        os.makedirs(results_dir, exist_ok=True)

        filename = f'{results_dir}/{field_name}_{campaign_name}_{action_id}_discmag_test.csv'
        row.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)
    
    return filename



# concatenate all individual actions then after. So essentially adding more actions/nights of observation to eachother to get whole dataset of the campaign
def concatenate_actions(actions, field_name, campaign_name):

    dfs = []

    for action in actions:

        action_id = int(action.split('/')[-2].split('_')[0].replace('action', ''))      # getting action id again
        filename = f'test_results/{field_name}/{campaign_name}/{field_name}_{campaign_name}_{action_id}_discmag_test.csv'      # defining the name of the files

        if os.path.exists(filename):    # if an observations file exists for this action, add it to the dataframe containing the file names
            dfs.append(pd.read_csv(filename))
        else:
            print(f'warning: {filename} not found, skipping')   # if there's no file, skips

    # making a master dataframe for the entire campaign within a field by concatenating all of the individual action files
    full_df = pd.concat(dfs, ignore_index=True)
    full_df = full_df.sort_values('MJD').reset_index(drop=True)    # making sure they are in order of time in case things get mixed up 

    results_dir = f'test_results/{field_name}/{campaign_name}'
    os.makedirs(results_dir, exist_ok=True)
    full_df.to_csv(f'{results_dir}/{field_name}_{campaign_name}_discmag_test_full.csv', index=False)       # converting it to a csv

    return full_df 



# then I would say for obj in obj_names where obj_names is the list of potential candidates (not including comp stars)
def plot_lightcurve(obj, flux_data, field_name, campaign_name):
    
    # THEN I would have a loop that says for action in actions which is a list of actions, run this function and then concatinate all the actions together
    plt.scatter(flux_data['MJD'], flux_data[f'{obj}_flux'], s=0.1, color='black')
    plt.title(f'{obj} light curve')
    plt.xlabel('MJD')
    plt.ylabel('Flux')
    #plt.axvline(disc_mjd, color='red', linestyle='--', label='Discovery MJD')
    plt.legend()

    lc_dir = f'lightcurves/{field_name}/{campaign_name}'
    os.makedirs(lc_dir, exist_ok=True)
    plt.savefig(f'{lc_dir}/{obj}_discmag_test_lightcurve_notnorm.png')
    plt.show()


# would have another function here that plots the comparison star normalised light curve
def comp_norm(obj, field_name, campaign_name): 

    df = pd.read_csv(f'test_results/{field_name}/{campaign_name}/{field_name}_{campaign_name}_discmag_test_full.csv')
    df_fields_obs = pd.read_csv('fields_and_observing_times_corrected.csv')
    comp_df = pd.read_csv(f'field_info/{field_name}/{field_name}_discmag_comparison_stars.csv')
    
    mjd = df['MJD']
    row = df_fields_obs[(df_fields_obs['field_name'] == field_name)]
    start_mjd = row['start_time (mjd)'].values[0]
    disc_mjd = start_mjd + 30 

    obj_flag = df[f'{obj}_flag']
    obj_flux = df[f'{obj}_flux']
    obj_fluxerr = df[f'{obj}_flux_err']
    source_ids = comp_df['source_id']

    rms_norm_fluxes = np.zeros(len(source_ids))

    for i in range(len(source_ids)):

        source_id = source_ids[i]
    
        flux = df[f'{source_id}_flux']
        med_norm_flux = flux/np.median(flux)

        rms_norm_flux = np.sqrt(np.mean((med_norm_flux - 1) ** 2))
        rms_norm_fluxes[i] = rms_norm_flux

        if i == 0:
            comp = df[f'{source_id}_flux'].to_numpy()
            comp_err = df[f'{source_id}_flux_err'].to_numpy()
            comp_flag = df[f'{source_id}_flag'].to_numpy()
        else:
            comp = np.vstack((comp, df[f'{source_id}_flux'].to_numpy())) # makes big stack of all the comp fluxes
            comp_err = np.vstack((comp_err, df[f'{source_id}_flux_err'].to_numpy()))
            comp_flag = np.vstack((comp_flag, df[f'{source_id}_flag'].to_numpy()))


    percentile_cut = np.nanpercentile(rms_norm_fluxes, 84)
    flag_bool = comp_flag != 0
    flag_frac = np.count_nonzero(flag_bool, axis=1)/ comp_flag.shape[1]

    comp_mask = (rms_norm_fluxes < percentile_cut) & (flag_frac < 0.01) # only use comps that have rms below 84th percentile and less than 1% flagged data
    good_comp = comp[comp_mask]
    good_comp_err = comp_err[comp_mask]
    good_comp_flag = comp_flag[comp_mask]

    print(f"Number of comparison stars suriving the cut: {np.count_nonzero(comp_mask)}")

    master_comp = np.sum(good_comp, axis=0)
    master_comp_err = np.sqrt(np.sum(good_comp_err ** 2, axis=0))
    master_comp_flag = np.sum(good_comp_flag, axis=0)   

    mask= (obj_flag == 0)
    corrected_flux = obj_flux[mask] / master_comp[mask]
    corrected_flux_err = obj_fluxerr[mask] / master_comp[mask]
    mjd = mjd[mask]

    med_flux = np.median(corrected_flux[mjd < disc_mjd])
    corrected_flux /= med_flux
    corrected_flux_err /= med_flux

    return mjd, corrected_flux, corrected_flux_err, disc_mjd



def plot_compnorm_lc(mjd, corrected_flux, disc_mjd, obj, field_name, campaign_name):

    plt.scatter(mjd, corrected_flux, s=0.1, color='black')
    plt.title(f'{obj} light curve')
    plt.xlabel('MJD')
    plt.ylabel('Median normalised flux')
    plt.axvline(disc_mjd, color='red', linestyle='--', label='Discovery MJD')
    plt.legend()

    lc_dir = f'lightcurves/{field_name}/{campaign_name}'
    os.makedirs(lc_dir, exist_ok=True)
    plt.savefig(f'{lc_dir}/{obj}_discmag_test_compnorm_lc.png', dpi=200, bbox_inches='tight')
    plt.show()

def plot_binned_lc(mjd, corrected_flux, disc_mjd, obj, field_name, campaign_name):

    bin_width = 1/24  
    bins = np.arange(mjd.min(), mjd.max() + bin_width, bin_width)
    bin_idx = np.digitize(mjd, bins)

    binned_time = np.array([mjd[bin_idx == i].mean() for i in np.unique(bin_idx)])
    binned_flux = np.array([corrected_flux[bin_idx == i].mean() for i in np.unique(bin_idx)])

    plt.scatter(mjd, corrected_flux, s=1, label='raw', color='grey', alpha =0.5)
    plt.scatter(binned_time, binned_flux, s=4, color='black', label='binned')
    plt.title(f'{obj} light curve')
    plt.xlabel('MJD')
    plt.ylabel('Median normalised flux')
    plt.axvline(disc_mjd, color='red', linestyle='--', label='Discovery MJD')
    plt.legend()

    lc_dir = f'lightcurves/{field_name}/{campaign_name}'
    os.makedirs(lc_dir, exist_ok=True)
    plt.savefig(f'{lc_dir}/{obj}_discmag_test_binned_lc.png', dpi=200, bbox_inches='tight')
    plt.show()
        
