# QUB ARC Project — Mapping the Transient Sky with NGTS

## Overview
The Next Generation Transit Survey (NGTS) is a ground-based telescope at the 
Paranal Observatory in Chile, whose primary function is to search for transiting 
exoplanets. With its high photometric precision and a cadence of 13 seconds, 
NGTS provides a unique opportunity to study transient phenomena in detail.

This project aims to produce high-coverage lightcurves for transient objects observed 
by NGTS, using its archival data.

## Files
- `wget_pp.py` — downloads raw images from NGTS archival data using parallel processing
- `phot_pipeline_withfuncs.py` — the main photometry pipeline
- `functions.py` — contains the functions used by the photometry pipeline

## Notes
While the photometry runs correctly, the plotting within `phot_pipeline_withfuncs.py` 
is currently poor. Manual inspection in a separate file is generally needed to 
obtain good lightcurves about the explosion epoch of the transient.
