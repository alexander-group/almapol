# ALMA Polarization Calibration Pipeline (almapol)

[![DOI](https://zenodo.org/badge/1279385213.svg)](https://doi.org/10.5281/zenodo.20836850)

Code for reducing full polarization continuum observations from ALMA. 

This pipeline is designed to automate and guide the reduction process, split into two primary stages (Pre-calibration and Calibration), followed by optional self-calibration, point source fitting, and polarization variability analysis.

---

## Prerequisites

- **CASA**: The pipeline must be run inside a CASA (Common Astronomy Software Applications) environment. CASA version 6.x is recommended.
- **Dependencies**: The auxiliary scripts require standard Python libraries such as `numpy`, `matplotlib`, and `urllib` (typically pre-installed in CASA's Python environment).
- **HPC/MPI**: For large datasets, running CASA with MPI (`mpicasa`) is highly recommended.

---

## Usage

How to access the ALMA polarization calibration scripts.

### Setup

Here are the instructions for cloning the `almapol` repository to your HPC home directory:

1. Check if you have an `~/.ssh/id_rsa.pub` file. If so, skip to step 3.
2. If not, generate one by running:
   ```bash
   ssh-keygen
   ```
   Press enter through the prompts to accept the defaults.
3. Run `cat ~/.ssh/id_rsa.pub` and copy the output contents.
4. Navigate to GitHub.
5. Click on your profile photo in the top right corner and select **Settings**.
6. Navigate to the **SSH and GPG keys** tab on the left.
7. Click **New SSH key** in the top right, give it a descriptive name, and paste the copied public key into the **Key** field.
8. Clone the repository using SSH:
   ```bash
   git clone git@github.com:alexander-group/almapol.git
   ```

From now on, run `cd ~/almapol && git pull` before starting a data reduction to ensure you are using the most up-to-date scripts!

---

## Running the Pipeline

The calibration process is divided into two sequential stages.

### Stage 1: Pre-Calibration (`alma_precal.py`)

This stage imports the ASDMs, generates listing files, applies a priori flags, runs Tsys and WVR calibration, concatenates the observations, and splits the data.

1. **Setup**:
   - Copy [`almapol/alma_precal.py`](almapol/alma_precal.py) and [`almapol/config.py`](almapol/config.py) into your current working directory.
   - Create symbolic links for the necessary files (don't forget the trailing dot `.`):
     ```bash
     ln -s /path/to/measurement/sets/*.ms .
     ln -s /path/to/almapol/almapol/util.py .
     ln -s /path/to/almapol/almapol/calibrate.py .
     ```
   - Start CASA (using MPI if available):
     ```bash
     ml casa
     mpicasa -n 17 $(which casa)
     ```
2. **Import**:
   - Edit [`config.py`](config.py) to set the `date`, `band`, and `basename` list.
   - Set `doimport = True` in [`config.py`](config.py).
   - In CASA, execute:
     ```python
     run -i "alma_precal.py"
     ```
3. **Listobs** (requires manual inspection):
   - Set `dolistobs = True` in [`config.py`](config.py) and re-run `alma_precal.py`.
   - Open the generated `.listobs.txt` files to identify and update: `fieldnames`, `tsysfields_self`, `tsysfields_alt`, `tsysfields_ref`, `spw0`, and `spwmax` in [`config.py`](config.py). *You will need to search the logs/text files to determine the base spectral window `spw0` for later calibration scaling.*
4. **Apriori Flags**:
   - Set `aprioriflags = True` in [`config.py`](config.py) and re-run `alma_precal.py`.
5. **Fix Syscal Times**:
   - Set `dofixsyscaltimes = True` in [`config.py`](config.py) and re-run `alma_precal.py`.
6. **Tsys and WVR Calibration**:
   - Set `docalibrate = True`, `dogencal = True` and re-run `alma_precal.py`.
   - Set `docalibrate = True`, `dogencal = False`, `doapplycal = True` and re-run `alma_precal.py`.
7. **Concat**:
   - Set `docalibrate = False`, `doapplycal = False`, `doconcat = True` and re-run `alma_precal.py`.
8. **Split**:
   - Run `listobs` on the concatenated Measurement Set to determine the science spectral windows and set `sciencespw` in [`config.py`](config.py).
   - Set `doconcat = False`, `dosplit = True` and re-run `alma_precal.py`.

---

### Stage 2: Calibration & Polarization (`calibrate.py`)

This stage derives the parallel-hand and cross-hand/leakage calibrations, and applies them to your calibrators and targets.

1. **Setup**:
   - Run `listobs` on the output of the split command from Stage 1. Identify the field names for polarization (`Lcal`), bandpass (`Bcal`), flux (`Fcal`), and gain (`Gcal`) calibrators, and enter them in [`config.py`](config.py).
   - Run `plotants` to select a reference antenna near the center of the array, and set `refant` in [`config.py`](config.py).
2. **Derive Parallel-Hand Calibration**:
   - Set `dosplit = False`, `docal_SetJy = True`, `doflagedge = True`, `docal_Bandpass = True`, `docal_Gain = True`, `docal_Fluxscale = True` in [`config.py`](config.py).
   - Run in CASA:
     ```python
     run -i "calibrate.py"
     ```
   - Check the `setjy.last` file in the terminal to verify and record the flux calibrator's flux density and spectral index.
   - Inspect `fig7.png` for bandpass solutions. Flag data as necessary, remove the calibration tables, and repeat this step if flags were modified.
3. **Apply Parallel-Hand and Start Polarization Calibration**:
   - Set `docal_SetJy = False`, `doflagedge = False`, `docal_Bandpass = False`, `docal_Gain = False`, `docal_Fluxscale = False`, `applycal_ParallelHand = True`, `dopol_Gain = True` in [`config.py`](config.py).
   - Re-run `calibrate.py`.
   - Inspect `fig8.png` (flux calibrator) and `fig9.png` (gain calibrator) for polarization structure in gains.
   - Check `fig10-prelim.png` (leakage calibrator) for the gain amplitude ratio, flag bad data if necessary, and re-run this step.
4. **Determine the Kcrs Scan**:
   - Set `applycal_ParallelHand = False`, `dopol_Gain = False`, `dopol_ApplyGainBP = True`, `dopol_QU = True` in [`config.py`](config.py).
   - Re-run `calibrate.py`.
   - This opens the `plotms` GUI and saves `fig10.png`. Identify a scan showing average polarization values and set `polscan` in [`config.py`](config.py) to this scan number.
   - Check `fig11.png` for any data requiring flags.
   - Note the derived polarization of the leakage calibrator outputted to the terminal and save it for your records.
5. **Derive the Cross-Hand Delay**:
   - Set `dopol_ApplyGainBP = False`, `dopol_QU = False`, `dopol_CrossHandDelay = True` in [`config.py`](config.py).
   - Re-run `calibrate.py`.
   - In the `plotms` GUI, page through the baselines relative to `refant` (one is saved as `fig12.png`). Note that phase scatter on low S/N scans is normal.
6. **Apply Cross-Hand Delay & Solve for XY Phase**:
   - Set `dopol_CrossHandDelay = False`, `dopol_ApplyKcrs = True`, `dopol_XYphase = True` in [`config.py`](config.py).
   - Re-run `calibrate.py`.
   - Inspect `fig13.png` to confirm the phases have been flattened (residual non-linear scatter is resolved in the cross-hand bandpass).
   - Inspect `fig14.png` to check for opposite color signatures (indicating the reference antenna's non-zero cross-hand phase).
7. **Derive Instrumental Leakage & Cross-Hand Bandpass**:
   - Set `dopol_ApplyKcrs = False`, `dopol_XYphase = False`, `dopol_ApplyXYphase = True`, `dopol_RegenLcalGains = True`, `dopol_Leakage = True`, `dopol_XYamp = True` in [`config.py`](config.py).
   - Re-run `calibrate.py`. This generates:
     - `fig17.png`: Verify the phase ramp has been successfully removed.
     - `fig18a.png`/`fig18b.png`: Verify the second plot accounts for the leakage calibrator's intrinsic polarization.
     - `fig19.png`, `fig20.png`, `fig21.png` (a and b): Verify leakage amplitude, real, and imaginary components across the array are flat. Run custom `plotms` commands in CASA to inspect all antennas:
       ```python
       plotms(vis=msname+'.Df0gen', xaxis='frequency', yaxis='amp', spw='0~3', iteraxis='antenna', coloraxis='corr', gridrows=2, gridcols=2, showgui=True)
       ```
     - `fig22.png` and `fig23.png`: Cross-hand gain amplitudes and amplitude ratios (should be close to 1).
   - Record the residual polarization of the leakage calibrator from the terminal output (it should be very small).
8. **Verify Leakage Calibrator Calibration**:
   - Set `dopol_ApplyXYphase = False`, `dopol_RegenLcalGains = False`, `dopol_Leakage = False`, `dopol_XYamp = False`, `applycal_Lcal = True` in [`config.py`](config.py).
   - Re-run `calibrate.py`. This produces:
     - `fig26.png`: Imaginary vs. Real (signal should be entirely real).
     - `fig27.png`/`fig28.png`: Calibrated amplitude/phase vs. frequency (parallel hands should be ~1, cross-hands should be small, phase should be 0 or 180 degrees).
9. **Apply to Target and Split Data**:
   - Set `applycal_Lcal = False`, `applycal_Trgt = True`, `dosplit_Target = True`, `dosplit_Gcal = True`, `dosplit_Lcal = True` in [`config.py`](config.py).
   - Re-run `calibrate.py` to create the final split Measurement Sets and generate `fig30.png`/`fig31.png` showing the Stokes signals before and after calibration.

---

## Interactive Self-Calibration (`imaging.py`)

For targets requiring self-calibration, [`almapol/imaging.py`](almapol/imaging.py) provides an interactive loop to perform phase and amplitude self-cal cycles:
- It computes the optimal clean cellsize based on antenna UVW coordinates.
- It calculates the minimum recommended solution interval (`t_sol`) for each self-cal cycle.
- It prompts the user for solution intervals and calibration modes (phase-only `'p'` or amp+phase `'ap'`), runs `gaincal` and `applycal`, and shows diagnostic plots before asking whether to proceed or repeat the step.

To use:
1. Copy or symlink [`almapol/imaging.py`](almapol/imaging.py) to your working directory.
2. Edit the variables at the top of [`imaging.py`](imaging.py) (e.g., `main_vis`, `target`, `refant`, and `split_from_main`).
3. Run CASA and execute:
   ```python
   execfile("imaging.py")
   ```

---

## Point-Source Fitting & Variability Analysis (`imgfitpoltasks.py`)

The [`almapol/imgfitpoltasks.py`](almapol/imgfitpoltasks.py) script contains helper tasks to analyze Stokes images (`IQUV` and polarized intensity `P` maps):

- **Point-Source Fitting (`dopointsourcefit`)**: Automatically locates the Stokes-I peak, defines on/off-source regions based on the synthesized beam shape, performs multi-Stokes component fitting using CASA `imfit`, measures local RMS noise levels, and appends the values (RA, Dec, Flux, Error, RMS) to `results.txt`.
- **Per-Scan Imaging & Fit (`dovartests`)**: Automates imaging per scan range and runs point source fits to produce a timeline of flux density and polarization parameters.
- **Variability Plotting (`doplotpolvary`)**: Reads the tabular scan outputs, calculates offsets, fractions, and errors relative to a reference time, and produces polarization variability plots (`QUV` offsets or fractions).

---

## Directory Structure

The table below describes the layout of files and folders in this repository:

| Path | Description |
| :--- | :--- |
| [`.github/`](.github) | Directory containing GitHub configuration files and workflows. |
| └── [`.github/workflows/zenodo.yml`](.github/workflows/zenodo.yml) | GitHub Actions workflow to publish releases to Zenodo or Zenodo Sandbox. |
| [`almapol/`](almapol) | Directory containing all calibration, imaging, and fitting Python scripts. |
| ├── [`almapol/alma_precal.py`](almapol/alma_precal.py) | Stage 1 pre-calibration pipeline. Prepares ASDMs, generates listing files, and handles initial calibration (Tsys/WVR). |
| ├── [`almapol/calibrate.py`](almapol/calibrate.py) | Stage 2 calibration pipeline. Performs parallel-hand, cross-hand, and leakage calibration. |
| ├── [`almapol/config.py`](almapol/config.py) | Configuration template where paths, calibrator names, science SPWs, and pipeline step toggles are defined. |
| ├── [`almapol/imaging.py`](almapol/imaging.py) | Interactive self-calibration loop script (calculates cell sizes, runs `tclean` and `applycal`). |
| ├── [`almapol/imgfitpoltasks.py`](almapol/imgfitpoltasks.py) | Fits point sources to Stokes I/Q/U/V and polarized intensity images. Supports variability analysis. |
| ├── [`almapol/plotcommands.py`](almapol/plotcommands.py) | Collection of CASA `plotms` commands corresponding to steps in standard NRAO polarization guides. |
| ├── [`almapol/poltutorial-plotcommands.py`](almapol/poltutorial-plotcommands.py) | CASA `plotms` commands customized for the 3C286 Band 6 polarization calibration guide tutorial dataset. |
| ├── [`almapol/util.py`](almapol/util.py) | Utility functions for frequency conversions, querying the ALMA online flux database, and parsing XML VOTables. |
| [`.gitignore`](.gitignore) | Specifies patterns for files and directories (like CASA output files and logs) that git should ignore. |
| [`.zenodo.json`](.zenodo.json) | Metadata description file used by Zenodo to automatically populate release records. |
| [`LICENSE`](LICENSE) | The license terms for the repository. |
| [`README.md`](README.md) | This documentation file. |


