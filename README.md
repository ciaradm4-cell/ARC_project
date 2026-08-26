# QUB ARC Project - Mapping the transient sky with NGTS
The Next Generation Transit Survey  is a ground-based telescope based at the Paranal Observatory, Chile who's primary function is to search for transiting exoplanets. With it's high photometric precision and cadence of 13 seconds, the NGTS facility provides a unique opportunity to study transient phenomena in great detail. 

The main function of this work is to produce high-coverage lightcurves for transient objects observed by NGTS using its archival data. The download file (wget_pp.py), which uses parallel processing, grabs the raw images from NGTS, and the photometry pipeline used is outlined in phot_pipeline_withfuncs.py. Additionally, the functions.py file explicitly contains the functions used in the photometry pipeline. 

(Note that while the photometry runs correctly, the plotting within this file is poor and generally manual inspection in a seperate file is necessary to obtain clear lightcurves centered about the explosion.)
