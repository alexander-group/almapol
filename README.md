# almapol

Code for reducing full polarization continuum observations from ALMA

## Usage

How to access the alma polarization calibration scripts

### Setup

Here's some instructions for getting the alma polarization scripts from github into your HPC home directory:

1. Check if you have an` ~/.ssh/id_rsa.pub`  file, if so skip to step 3
2. If not, you need to generate one by using the command `ssh-keygen`  and then just keep hitting enter until it creates it
3. Run the command `cat ~/.ssh/id_rsa.pub`  and copy the contents
4. Navigate to GitHub
5. Click on your profile photo in the top right corner
6. Click on "Settings"
7. Navigate to the "SSH and GPG keys" tab on the left
8. Click "New SSH key" in the top right, name it whatever you'd like, and paste the contents that you copied in step 3 into the box labelled "Key"
9. Now you should be able to clone the repo from the ssh link to your hpc home directory using the command `git clone git@github.com:alexander-group/almapol.git`

From now on you should just `cd ~/almapol && git pull`  everytime you are about to start reducing data to make sure you have the most up to date versions of the scripts!

### Running the Pipeline

How to run the alma polarization calibration scripts

#### Stage 1: precal
- setup
   1. Copy alma-precal.py and config.py into the current working directory
   2. Make the following symlinks with ln -s filepath . (don't forget the dot):
	  - The measurement sets
	  - util.py
	  - calibrate.py (needed in Stage 2)
   3. Start casa using ml casa followed by mpicasa -n 17 $(which casa)
- import
  1. Make the following edits to config.py: Set the date, band, and base names	
  2. set doimport=True
  3. Run alma-precal using run -i "alma-precal.py"
- listobs (this requires the most manual intervention)
  1. set dolistobs=True and re-run alma-precal 
  2. Use the outputs to set fieldnames, tsysfields, spw0, spwmax _you will need to dig through the saved listobs outputs to figure out spw0 (this is needed for applycal later)_
- aprioriflags
  1. set aprioriflags=True and re-run alma-precal
- fixsyscaltimes
  1. set dofixsyscaltimes=True and re-run alma-precal
- Tsys and WVR calibration
  1. set docalibrate = True, dogencal = True and re-run alma-precal
  2. set docalibrate = True, dogencal = False, doapplycal = True and re-run alma-precal 
- Concat
  1. set docalibrate = False, doapplycal = False, doconcat = True and re-run alma-precal
- Split
  1. Run listobs and determine science spws, set sciencespw
  2. set doconcat = False, dosplit = True and re-run alma-precal
	
#### Stage 2: calibrate.py
- run listobs on the output of the split command from Stage 1. Determine the targets to be used as polarization, bandpass, flux density, and gain calibrators; enter their names in config.py
- run plotants and pick a reference antenna near the center of the array; set refant. 
- Derive parallel hand calibration
Set dosplit = False, docal_SetJy = True, doflagedge = True, docal_Bandpass = True, docal_Gain = True, docal_Fluxscale = True
	1. run -i "calibrate.py"
	2. more setjy.last on the terminal and record the flux calibrator's flux and spectral index 
	3. Check fig7.png for bandpass solutions, flag data as necessary, delete the calibration tables, and repeat the calibrations if needed. 
- Apply parallel hand calibration and start polarization calibration
  1. Set docal_SetJy = False, doflagedge = False, docal_Bandpass = False, docal_Gain = False, docal_Fluxscale = False, applycal_ParallelHand = True, dopol_Gain = True
  2. run -i "calibrate.py"
  3. Check fig8 (flux cal) and fig9 (gain cal) for polarization structure in gains
  4. Check fig10-prelim (Lcal) for gain amp ratio and flag data as necessary; then re-run this step
- Determine the scan to use for Kcrs
  1. Set applycal_ParallelHand = False, dopol_Gain = False, dopol_ApplyGainBP = True, dopol_QU = True
  2. run -i "calibrate.py"
  3. This will bring up the plotms gui (and save fig10.png). Select a scan that is near the average value and set the polscan parameter in config.py.
  4. Also check fig11.png for any data that needs to be flagged.
  5. Check the terminal output for the derived polarization of the leakage calibrator and save this information to a text file.
- Derive the cross-hand delay
  1. Set dopol_ApplyGainBP = False, dopol_QU = False, dopol_CrossHandDelay = True
  2. run -i "calibrate.py"
  3. This will bring up the plotms gui. Page through the baselines to the refant. One of these will be saved to disk. Phases will be scattered on scans with low S/N (this is expected).
- Apply the Cross-hand delay solutions to the leakage calibrator, and derive the cross-hand phase of the reference antenna
  1. Set dopol_CrossHandDelay = False, dopol_ApplyKcrs = True, dopol_XYphase = True
  2. run -i "calibrate.py"
  3. This will make fig13 – check that the phases have been flattened (there may still be non-linear scatter, which will be taken out later in the cross-hand bandpass). 
  4. This will also make fig14 – this should show opposite signatures in the two colors, indicative of the non-zero cross-hand phase of the reference antenna. 
  5. This will also make fig15 – this is not particularly useful.
- Apply the cross-hand phase of the reference antenna and derive the rest of the polarization calibrations, including the instrumental polarization
  1. Set dopol_ApplyKcrs = False, dopol_XYphase = False, dopol_ApplyXYphase = True, dopol_RegenLcalGains = True, dopol_Leakage = True, dopol_XYamp = True  
  2. This will make
    - fig 17: check that the phase ramp has now been taken out
	- fig 18a and b: the second is with the updated gain table that now accounts for the leakage calibrator's intrinsic polarization
	- fig 19, 20, and 21 (a and b) – plots of leakage amp vs freq, real vs freq, and imaginary vs freq, respectively, for six of the antennas of the array. Check that there are no strong structures in these. To check all the antennas, run the plotting commands yourself. 
   ```
			plotms(vis=msname+'.Df0gen',xaxis='frequency',yaxis='amp',spw='0~3',iteraxis='antenna',coloraxis='corr',gridrows=2,gridcols=2,showgui=True)
	```
	… and replace "amp" with "real" and "imaginary" for the other plots


	3. Check the terminal output for the residual polarization of the leakage calibrator (should be small) and save it to a text file. 
	4. figs 22 and 23: the cross-hand gain amplitudes and amplitude ratios (both should be near 1)
- Apply the polarization calibration to the polarization calibrator and verify the results
  1. Set dopol_ApplyXYphase = False, dopol_RegenLcalGains = False, dopol_Leakage = False, dopol_XYamp = False, applycal_Lcal = True
  2. This will make the following plots for the leakage calibrator
	 - fig 26: imaginary vs real – signal should be entirely real
	- fig 27: calibrated amp vs frequency (all 4 corrs) – parallel hands should be 1, cross-hands will be low (but non-zero if the calibrator has some polarization)
	- fig 28: calibrated phase vs frequency (all 4 corrs) – should be zero (or 180 degrees)
	- fig 29: Same as Fig 28, but for one baseline
-  Apply the calibration to the other calibrators and the target; split off the corrected data
   1. Set applycal_Lcal = False, applycal_Trgt = True, dosplit_Target = True, dosplit_Gcal = True, dosplit_Lcal = True 
   2. This will make figs 30 and 31 (imag vs real before and after calibration, respectively) for the target. The imaginary parts should be close to zero (clearer with larger Stokes I)
