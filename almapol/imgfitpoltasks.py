# This script does point source fits to images (an IQUV image and a P image)
# It's most useful for images created by the pipeline
# Created by Tanmoy Laskar on 2025-Feb-10
# Updated to work on a range of different fits files
# Updated to turn the fitting into a function; script renamed from imgfitpol_ALMApipeFITS.py to imgfitpoltasks.py
# Updated to include variability analysis - imaging and fitting
# Updated to include variability analysis - plotting

import numpy as np
import os

def dopointsourcefit(IQUVname, Pname, Numbeams=6, resbox_offset_factor=1.4,
                     fixpos_to_I=True, useresidualimage=False, resimg=None,
                     writeresults=True, estimatesname='estimates'):
    """
    Fit point-source components to Stokes images and optionally to a polarization (P) image.

    This function:
    - finds the Stokes-I peak,
    - builds on-source and off-source boxes sized in beams,
    - runs CASA-like `imfit` on I, Q, U, V (and P if provided),
    - measures local rms (either from image or residual image),
    - optionally appends a line to a results file (default 'results.txt'),
    - returns a dict with fit quantities.

    Parameters
    ----------
    IQUVname : str
        Path to the combined I/Q/U/V image (CASA image name).
    Pname : str or None
        Path to the P image (pol intensity) or None to skip P.
    Numbeams : int, optional
        Box side in number of beams used for the on-source fit. Default 6.
    resbox_offset_factor : float, optional
        Factor (times `Numbeams`) to offset the off-source rms box away from source. Default 1.4.
    fixpos_to_I : bool, optional
        If True, fix fitted position of Q/U/V/P to the I-fit position. Default True.
    useresidualimage : bool, optional
        If True, use the provided `resimg` (residual) for rms calculation; otherwise use an offset box on the image.
    resimg : str or None, optional
        Path to the residual image if `useresidualimage` is True.
    writeresults : bool, optional
        If True, append results to `results.txt`. Default True.

    Returns
    -------
    dict
        Dictionary containing measured values. Typical keys:
        - "q" (frequency),
        - "I", "dI", "Irms", "I_ra", "I_dra", "I_dec", "I_ddec",
        - similarly for Q, U, V, P (if present).
    """
    resbox_offset = int(Numbeams * resbox_offset_factor)

    # Find location of Stokes I peak
    imstat_results_dict = imstat(IQUVname)
    x, y = imstat_results_dict['maxpos'][0:2]

    # Get beam properties
    imhead_results_dict = imhead(IQUVname)
    if 'perplanebeams' in imhead_results_dict:
        B = imhead_results_dict['perplanebeams']['beams']
        # perplanebeams structure: using the same indexing as your original script
        bmaj = B['*0']['*0']['major']['value']
        bmajunit = B['*0']['*0']['major']['unit']
        bmin = B['*0']['*0']['minor']['value']
        bminunit = B['*0']['*0']['minor']['unit']
        bpa = B['*0']['*0']['positionangle']['value']
        bpaunit = B['*0']['*0']['positionangle']['unit']
    elif 'restoringbeam' in imhead_results_dict:
        Rbeam = imhead_results_dict['restoringbeam']
        bmaj = Rbeam['major']['value']
        bmin = Rbeam['minor']['value']
        # no unit provided here in your previous code; assume arcsec for sizes and deg for PA
        bmajunit = 'arcsec'
        bminunit = 'arcsec'
        bpa = imhead_results_dict.get('bpa', 0.0)
        bpaunit = 'deg'
    else:
        raise KeyError("'perplanebeams' or 'restoringbeam' not found in image header. Cannot determine beam shape.")

    # Build box for fitting
    pixscale = np.abs(imhead_results_dict['incr'][0] * 206265.0)  # arcsec/pixel
    Rbeam_meansize = np.sqrt(bmaj * bmin)                         # sqrt(beam area) in arcsec
    beampix = Rbeam_meansize / pixscale
    npix = int(np.floor(Numbeams * beampix))
    print("Pixel scale is {} arcsec".format(pixscale))
    print("Beam is {} x {} arcsec".format(bmaj, bmin))
    print("sqrt(beam area) is {} arcsec".format(Rbeam_meansize))
    print("Requested box size is {} beams on a side".format(Numbeams))
    print("Will attempt fit in a {}x{} pixel box centered at the source".format(npix, npix))
    if npix > imhead_results_dict['shape'][0]:
        raise AssertionError("Box to fit is larger than image size! Reduce Numbeams and rerun")

    srcbox = f"{x-npix},{y-npix},{x+npix},{y+npix}"
    print("Image Stokes I location is at pixel {}, {}".format(x, y))
    print("On-source box for fitting (in pixels):", srcbox)

    # Set up off-source box for rms calculation
    if useresidualimage:
        print("Will use residual images for rms calculation")
        resbox = srcbox
        # make xoff,yoff defined so prints don't crash
        xoff, yoff = x, y
    else:
        print("No residual image provided. Will use offset box for rms calculation")
        offsetpix = int(resbox_offset * beampix)
        print("Will offset off-source box by {} pixels in dec".format(offsetpix))
        xoff, yoff = x, y - offsetpix
        resbox = f"{xoff-npix},{yoff-npix},{xoff+npix},{yoff+npix}"
    print("Off-source box is centered at pixel {}, {}".format(xoff, yoff))
    print("Off-source box for rms (in pixels):", resbox)

    xypos = [None, None]
    if Pname is None:
        ilist, Slist = [0, 1, 2, 3], ['I', 'Q', 'U', 'V']
    else:
        ilist, Slist = [0, 1, 2, 3, 0], ['I', 'Q', 'U', 'V', 'P']

    resultsdict = {}

    for i, S in zip(ilist, Slist):
        print(f"Fitting {S} image")
        if S == 'P':
            img = Pname
            stokes = None
        else:
            img = IQUVname
            stokes = S

        fitfile = 'results.txt'
        # date-obs from header (CASA call)
        dateobs = imhead(imagename=img, mode='get', hdkey='date-obs')

        # Build estimates string. If fixing to I for non-I stokes, use xypos
        if fixpos_to_I and (S != 'I') and (xypos[0] is not None):
            est_x, est_y = xypos[0], xypos[1]
            # 'xyabp' tells CASA fit to fix x,y and fit amplitude/beam/pa (?) — keeping your original convention
            estimates = f"0.005,{est_x},{est_y},{bmaj}{bmajunit},{bmin}{bminunit},{bpa}{bpaunit},xyabp"
        else:
            estimates = f"0.005,{x},{y},{bmaj}{bmajunit},{bmin}{bminunit},{bpa}{bpaunit},abp"

        estimatesfile = estimatesname + '.txt'
        with open(estimatesfile, 'w') as f:
            f.write(estimates)

        resultsI = imfit(imagename=img, estimates=estimatesfile, box=srcbox, stokes=stokes)['results']['component0']
        xypos = resultsI['pixelcoords']
        q = resultsI['spectrum']['frequency']['m0']['value']
        ra = resultsI['shape']['direction']['m0']['value']
        dra = resultsI['shape']['direction']['error']['longitude']['value']
        dec = resultsI['shape']['direction']['m1']['value']
        ddec = resultsI['shape']['direction']['error']['latitude']['value']

        # flux values: multiply by 1000 to get mJy (your original script did this)
        Fval = resultsI['flux']['value'][i] * 1000.0
        dF = resultsI['flux']['error'][i] * 1000.0

        # Determine the rms
        if useresidualimage and (resimg is not None):
            results2 = imstat(imagename=resimg, box=resbox, stokes=stokes)['sigma'][0] * 1000.0
        else:
            results2 = imstat(imagename=img, box=resbox, stokes=stokes)['sigma'][0] * 1000.0

        # Write results to fitfile (append)
        if writeresults:
            with open(fitfile, 'a') as f:
                f.write(dateobs + ', ' + str(q) + ', ' + S + ', ' +
                        str(ra) + ', ' + str(dra) + ', ' + str(dec) + ', ' + str(ddec) +
                        ', ' + str(Fval) + ', ' + str(dF) + ', ' + str(results2) + '\n')

        # Update resultsdict (use clear string keys)
        entry = {
            "q": q,
            f"{S}_ra": ra,
            f"{S}_dra": dra,
            f"{S}_dec": dec,
            f"{S}_ddec": ddec,
            S: Fval,
            f"d{S}": dF,
            f"{S}rms": results2
        }
        resultsdict.update(entry)

    return resultsdict


def mkimage(msname, imgname, datacolumn='corrected', imsize=[512, 512], spw='', scan='', nsigma=2,
            interactive=False, parallel=False):
    """
    Make (tclean) and export CASA images from a Measurement Set.

    This is a light wrapper around CASA tasks that:
    - computes a rough cellsize from MS UVW and spectral info,
    - runs `tclean` (if the image directory doesn't already exist),
    - exports the image and residual to FITS (if not already exported).

    Notes
    -----
    - This function uses CASA table tool `tb`, `tclean`, and `exportfits`. It must be run
      in a CASA-enabled Python environment where those functions are available.
    - `imgname` is the base CASA imagename (not a .fits name). The CASA image directory
      will be `imgname+'.image'`.
    """
    # calculate cellsize using MS (assumes CASA tb tool)
    tb.open(msname)
    B_max = np.max(np.sqrt(tb.getcol('UVW')[0]**2 +
                           tb.getcol('UVW')[1]**2 +
                           tb.getcol('UVW')[2]**2))
    tb.close()

    tb.open(msname + '/SPECTRAL_WINDOW/')
    nu_max = np.mean(tb.getcol('REF_FREQUENCY'))
    tb.close()

    mycell = ((3.0e8 / nu_max) / B_max) * (180.0 / np.pi) * 3600.0 / 6.0

    # Run tclean if not already present
    if not os.path.isdir(imgname + '.image'):
        tclean(vis=msname,
               imagename=imgname,
               spw=spw,
               scan=scan,
               nsigma=nsigma,
               interactive=interactive,
               datacolumn=datacolumn,
               specmode='mfs',
               nterms=1,
               gain=0.1,
               cell=str(mycell) + 'arcsec',
               imsize=imsize,
               deconvolver='clarkstokes',
               stokes='IQUV',
               weighting='briggs',
               robust=0.0,
               niter=5000,
               parallel=parallel)

    # Export to FITS if not already present
    if not os.path.isfile(imgname + ".image.fits"):
        exportfits(imgname + '.image', fitsimage=imgname + ".image.fits")
    if not os.path.isfile(imgname + ".residual.fits"):
        exportfits(imgname + '.residual', fitsimage=imgname + ".residual.fits")


def dovartests(msnamebase="GRB210702A_2021-07-03",
               scanlist=['11~29', '36~54', '61~75'],
               SPW='0~3',
               targtype='gain',
               datacolumn='corrected',
               extrapostfix=''):
    """
    Make per-scan images for a measurement set, run the point-source fitter, and save results.

    This function:
    - constructs ms & image base names from `msnamebase` and `targtype`,
    - makes images (via mkimage) if needed,
    - splits out Stokes planes (I/Q/U/V),
    - computes P and A images (via immath),
    - runs `dopointsourcefit` on each scan,
    - appends results to a per-dataset text file.

    Parameters
    ----------
    msnamebase : str
        Base name for the measurement set files.
    scanlist : list of str
        Scan ranges used for imaging (e.g. ['11~29', '36~54']).
    SPW : str
        Spectral window selection '0~1', '2~3', or '0~3'.
    targtype : str
        Descriptor used for naming output files.
    """
    # Set up file names
    msname = msnamebase + "_" + targtype + '.ms'
    postfixdict = {'0~1': 'LSB', '2~3': 'USB', '0~3': 'all'}
    postfix = postfixdict[SPW]
    fitfile = msnamebase + '_varphotfits_' + targtype + '_' + extrapostfix + postfix + '.txt'
    imgbasename = msnamebase + "_" + targtype + '_varpol_' + extrapostfix + postfix

    stokeslist = ['I', 'Q', 'U', 'V']
    for scan in scanlist:
        img = imgbasename + '_scan' + scan[0:2] + scan[3:5]

        if not os.path.isdir(img + '.residual'):
            mkimage(msname, img, datacolumn=datacolumn, spw=SPW, scan=scan, nsigma=2, interactive=False, parallel=False)

        if not os.path.isdir(img + '.I.image'):
            for stokes in stokeslist:
                imsubimage(imagename=img + '.image', outfile=img + '.' + stokes + '.image', stokes=stokes)
            immath(outfile=img + '.P.image', mode='poli', imagename=[img + '.Q.image', img + '.U.image'])
            immath(outfile=img + '.A.image', mode='pola', imagename=[img + '.Q.image', img + '.U.image'])

        t = imhead(imagename=img + '.I.image', mode='get', hdkey='date-obs')
        fitresults = dopointsourcefit(img + '.image', img + '.P.image', writeresults=False, estimatesname=img+'_estimates')

        # Append results to file
        with open(fitfile, 'a') as f:
            f.write(str(scan) + ',' + t + ',' + str(fitresults['q']) + ', ' +
                    str(fitresults['I_ra']) + ', ' + str(fitresults['I_dra']) + ', ' +
                    str(fitresults['I_dec']) + ', ' + str(fitresults['I_ddec']) + ', ' +
                    str(fitresults['I']) + ', ' + str(fitresults['dI']) + ', ' + str(fitresults['Irms']) + ', ' +
                    str(fitresults['Q']) + ', ' + str(fitresults['dQ']) + ', ' + str(fitresults['Qrms']) + ', ' +
                    str(fitresults['U']) + ', ' + str(fitresults['dU']) + ', ' + str(fitresults['Urms']) + ', ' +
                    str(fitresults['V']) + ', ' + str(fitresults['dV']) + ', ' + str(fitresults['Vrms']) + ', ' +
                    str(fitresults['P']) + ', ' + str(fitresults['dP']) + ', ' + str(fitresults['Prms']) + ', ' + '\n')


def doplotpolvary(msnamebase="GRB210702A_2021-07-03", targtype='gain', postfix='all',
                  plotoffsets=False, T0='2022/09/21/11:05:59', norm="", extrapostfix=''):
    """
    Read the variable-photometry results file and create Q/U/V (and offsets) plots.

    - Reads msnamebase + '_varphotfits_' + targtype + '_' + extrapostfix + postfix  '.txt'
      (CSV-like file with columns: scan,t,q,ra,dra,dec,ddec,I,dI,Irms,Q,dQ,Qrms,U,dU,Urms,V,dV,Vrms,P,dP,Prms)
    - computes time since T0 (in hours),
    - computes summary statistics (mean, std, polarization fraction),
    - creates and saves plots named "<msnamebase>_varplot_<targtype>_<extrapostfix><postfix>_QUV*.png".

    Parameters
    ----------
    msnamebase : str
        Base name used to construct the results filename.
    targtype : str
        Target-type used in filename construction (e.g., 'gain').
    extrapostfix : additional file postfix if needed (passed to this function)
    postfix : str
        One of 'LSB', 'USB', or 'all' depending on SPW selection.    
    plotoffsets : bool
        If True, plot Q,U,V offsets from the mean (and normalize if requested).
    T0 : str
        Reference time string; accepted formats: YYYY/MM/DD/HH:MM:SS[.microsec] or with '-' instead of '/'.
        If empty, the first row in the file is used.
    norm : str
        Use "I" to normalize Q/U/V by Stokes I (plot fractions); otherwise plot in mJy.

    Notes
    -----
    - The function uses Python's native csv reader and numpy for numeric ops.
    - The results file must exist at the path:
      msnamebase + '_varphotfits_' + targtype + '_' + extrapostfix+postfix + '.txt'
    """
    varfitfile = msnamebase + '_varphotfits_' + targtype + '_' + extrapostfix+postfix + '.txt'
    plotbase = msnamebase + '_varplot_' + targtype + '_' + extrapostfix+postfix

    import numpy as np
    import matplotlib.pyplot as plt
    import datetime
    import csv

    fieldnames = [
        'scan', 't', 'q', 'ra', 'dra', 'dec', 'ddec',
        'I', 'dI', 'Irms',
        'Q', 'dQ', 'Qrms',
        'U', 'dU', 'Urms',
        'V', 'dV', 'Vrms',
        'P', 'dP', 'Prms'
    ]

    D_list = []
    if not os.path.exists(varfitfile):
        raise FileNotFoundError(f"File not found: {varfitfile}")

    with open(varfitfile, 'r', newline='') as f:
        first_line = f.readline()
        f.seek(0)
        if ',' in first_line:
            reader = csv.reader(f)
            for row in reader:
                row_dict = {name: value for name, value in zip(fieldnames, row)}
                D_list.append(row_dict)
        else:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                row = line.split()
                row_dict = {name: value for name, value in zip(fieldnames, row)}
                D_list.append(row_dict)

    N = len(D_list)
    if N == 0:
        raise ValueError("No data rows read from file: " + varfitfile)

    all_cols = fieldnames[:]
    col_data = {c: [] for c in all_cols}

    for row in D_list:
        for c in all_cols:
            v = row.get(c, '')
            if c in ('scan', 't'):
                col_data[c].append(v)
            else:
                try:
                    col_data[c].append(float(v.strip()))
                except Exception:
                    col_data[c].append(np.nan)

    numeric_cols = [c for c in all_cols if c not in ('scan', 't')]
    for c in numeric_cols:
        col_data[c] = np.array(col_data[c], dtype=float)

    col_data['scan'] = list(col_data['scan'])
    col_data['t'] = list(col_data['t'])

    def parse_time(s):
        s = s.strip()
        fmts = ["%Y/%m/%d/%H:%M:%S.%f", "%Y/%m/%d/%H:%M:%S"]
        for fmt in fmts:
            try:
                return datetime.datetime.strptime(s, fmt)
            except Exception:
                continue
        s2 = s.replace('-', '/')
        for fmt in fmts:
            try:
                return datetime.datetime.strptime(s2, fmt)
            except Exception:
                continue
        raise ValueError(f"Unrecognized timestamp format: '{s}'")

    if T0 == '':
        T0 = col_data['t'][0]
        print("No T0 provided, using first obs. T0= " + T0)
    else:
        print("Using provided T0 = " + T0)

    W0 = parse_time(T0)
    deltalist = []
    for T in col_data['t']:
        W = parse_time(T)
        delta = W - W0
        hours = delta.days * 24 + delta.seconds / 3600.0 + delta.microseconds / 3.6e9
        deltalist.append(hours)

    col_data['hours'] = np.array(deltalist, dtype=float)

    to_drop = ['scan', 't', 'ra', 'dra', 'dec', 'ddec', 'rms']
    for c in to_drop:
        if c in col_data:
            del col_data[c]

    meanI = np.nanmean(col_data['I'])
    meanQ = np.nanmean(col_data['Q'])
    meanU = np.nanmean(col_data['U'])
    meanV = np.nanmean(col_data['V'])
    meanP = np.nanmean(col_data['P'])

    stdI = np.nanstd(col_data['I'])
    stdQ = np.nanstd(col_data['Q'])
    stdU = np.nanstd(col_data['U'])
    stdV = np.nanstd(col_data['V'])
    stdP = np.nanstd(col_data['P'])

    Pi = 100.0 * col_data['P'] / col_data['I']

    print("Summary statistics for " + varfitfile)
    print("I  = ({:4.3f} +/- {:2.3f}) mJy".format(meanI, stdI))
    print("Q  = ({:4.3f} +/- {:2.3f}) mJy = ({:2.3%} +/- {:2.3%} of I)".format(
        meanQ, stdQ, abs(meanQ/meanI), abs(stdQ/meanI)))
    print("U  = ({:+4.3f} +/- {:2.3f}) mJy = ({:2.3%} +/- {:2.3%} of I)".format(
        meanU, stdU, abs(meanU/meanI), abs(stdU/meanI)))
    print("V  = ({:+4.3f} +/- {:2.3f}) mJy = ({:2.3%} +/- {:2.3%} of I)".format(
        meanV, stdV, abs(meanV/meanI), abs(stdV/meanI)))
    print("P  = ({:4.3f} +/- {:2.3f}) mJy = ({:2.3%} +/- {:2.3%} of I)".format(
        meanP, stdP, abs(meanP/meanI), abs(stdP/meanI)))

    deltaPi = np.nanmax(Pi) - np.nanmin(Pi)
    nmeas = len(Pi)
    print("Maximum deviation in pol fraction = {:2.3}% of I over {:d} measurements".format(deltaPi, nmeas))
    if nmeas == 3:
        print("Systematic polarization calibration uncertainty = {:2.3}% of I".format(deltaPi/1.69))

    if norm == "I":
        normfac = col_data['I']
        yunit = "(fraction of I)"
        postfix_out = '_frac'
    else:
        normfac = 1.0
        yunit = "(mJy)"
        postfix_out = '_mJy'

    plt.figure()
    artistlist = []
    plt.title(msnamebase, fontsize=14)
    plt.xlabel("Time since T0 (hours)", fontsize=14)

    dQ_abs = np.abs(col_data['dQ'])
    dU_abs = np.abs(col_data['dU'])
    dV_abs = np.abs(col_data['dV'])

    if plotoffsets:
        L = plt.errorbar(col_data['hours'], (col_data['Q'] - meanQ)/normfac, dQ_abs/normfac,
                         fmt='s', ms=10, color='C0', zorder=1); artistlist.append(L)
        L = plt.errorbar(col_data['hours'], (col_data['U'] - meanU)/normfac, dU_abs/normfac,
                         fmt='s', ms=10, color='C2', zorder=0); artistlist.append(L)
        L = plt.errorbar(col_data['hours'], (col_data['V'] - meanV)/normfac, dV_abs/normfac,
                         fmt='s', ms=10, color='C3', zorder=-1); artistlist.append(L)
        if norm == "I":
            namelist = [r"$(Q-\bar{Q})/\bar{I}$", r"$(U-\bar{U})/\bar{I}$", r"$(V-\bar{V})/\bar{I}$"]
        else:
            namelist = [r"$Q-\bar{Q}$", r"$U-\bar{U}$", r"$V-\bar{V}$"]
        plt.ylabel("Polarized flux offsets " + yunit, fontsize=14)
        plt.axhline(0, ls=':', color='k', zorder=-10)
        plt.legend(artistlist, namelist)
        plt.tight_layout()
        plt.savefig(plotbase + '_offsets' + postfix_out + '.png')
    else:
        L = plt.errorbar(col_data['hours'], col_data['Q']/normfac, dQ_abs/normfac,
                         fmt='s', ms=10, color='C0', zorder=1); artistlist.append(L)
        L = plt.errorbar(col_data['hours'], col_data['U']/normfac, dU_abs/normfac,
                         fmt='s', ms=10, color='C2', zorder=0); artistlist.append(L)
        L = plt.errorbar(col_data['hours'], col_data['V']/normfac, dV_abs/normfac,
                         fmt='s', ms=10, color='C3', zorder=-1); artistlist.append(L)
        if norm == "I":
            namelist = [r"$Q/I$", r"$U/I$", r"$V/I$"]
        else:
            namelist = [r"$Q$", r"$U$", r"$V$"]
        plt.ylabel("Polarized flux " + yunit, fontsize=14)
        plt.axhline(0, ls=':', color='k', zorder=-10)
        plt.title(msnamebase, fontsize=14)
        plt.legend(artistlist, namelist)
        plt.tight_layout()
        plt.savefig(plotbase + '_QUV' + postfix_out + '.png')

