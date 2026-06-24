###################################################
###### RUN EXECFILE TO IMPORT CONFIG ##############
###################################################
configfile = "config.py"
if os.path.exists(configfile):
    print(f"Running {configfile}...")
    execfile(configfile)
else:
    import warnings
    warnings.warn("No config file found in your working directory, please check that you have imported it!")

utilfile = "util.py"
if os.path.exists(utilfile):
    print(f"Running {utilfile}...")
    execfile(utilfile)
else:
    import warnings
    warnings.warn("No util file found at {utilfile}, please check that you have imported it!")

    
###################################################
###### A CHECK OF THE CONFIG VARS #################
###################################################

config_vars = [
    "date",
    "band",
    "basename",
    "fieldnames",
    "tsysfields_self",
    "tsysfields_alt",
    "tsysfields_ref",
    "spw0",
    "spwmax",
    "sciencespw",
    "doimport",
    "dolistobs",
    "aprioriflags",
    "dofixsyscaltimes",
    "docalibrate",
    "dogencal",
    "doapplycal",
    "clobberTsysTable",
    "clobberWVRTable",
    "doconcat",
    "dosplit",
    "verbose"
]

for v in config_vars:
    check_var(v)

###################################################
###### ACTUAL CALIBRATION STEPS ###################
###################################################

if (doimport):
    for name in basename:
        importasdm(asdm = name, asis='*')

if (dolistobs):
    import re
    for name in basename:
        os.system('rm '+name+'.listobs.txt')
        listobs(vis=name+'.ms', listfile=name+'.listobs.txt', verbose=True)
        path = name+'.listobs.txt'
        print('#######################################################')
        print(f"Summary for {name+'.listobs.txt'}")
        print()
        printed = {}

        with open(path, 'r') as file:
            for line in file:
                clean_line = re.sub(r'\s+', ' ', line)
                parts = clean_line.split()

                if re.search("CALIBRATE_FLUX", line, re.IGNORECASE) and "FLUX" not in printed:
                    printed["FLUX"] = parts[5]

                if re.search("OBSERVE_TARGET", line, re.IGNORECASE) and "TARGET" not in printed:
                    printed["TARGET"] = parts[5]

                if re.search("CALIBRATE_PHASE", line, re.IGNORECASE) and "GAIN" not in printed:
                    printed["GAIN"] = parts[5]

                if re.search("CALIBRATE_BANDPASS", line, re.IGNORECASE) and "BANDPASS" not in printed:
                    printed["BANDPASS"] = parts[5]

                if re.search("CALIBRATE_POLARIZATION", line, re.IGNORECASE) and "POL" not in printed:
                    printed["POL"] = parts[5]
        
        for k in ["FLUX","GAIN","TARGET","POL","BANDPASS"]:
            if k not in printed:
                printed[k] = "MISSING"
        
        print("FIELD INTENTS:")
        for key, value in printed.items():
            print(f"{value} \t # {key}")

        print()
        print("TSYS FIELDS:")
        print(f"fieldnames = ['{printed['FLUX']}','{printed['GAIN']}','{printed['TARGET']}','{printed['POL']}','{printed['BANDPASS']}']")
        print(f"tsysfields_self = ['{printed['FLUX']}','{printed['TARGET']}','{printed['POL']}','{printed['BANDPASS']}']")
        print(f"tsysfields_alt  = ['{printed['GAIN']}']")
        print(f"tsysfields_ref  = {{'{printed['GAIN']}':'{printed['TARGET']}'}}")

        print()
            
        spws_sci = []
        with open(path, 'r') as file:
            for line in file:
                clean_line = re.sub(r'\s+', ' ', line)
                parts = clean_line.split()
                if re.search("FULL_RES", line, re.IGNORECASE):
                    spws_sci.append(float(parts[0]))
                if re.search("CH_AVG", line, re.IGNORECASE):
                    spws_sci.append(float(parts[0]))
                    
        spwmax = int(max(spws_sci))
        print(f"Highest spectral window number in dataset: {spwmax}")

if (aprioriflags):
    for name in basename:
        flagdata(vis=name+'.ms',mode='manual', autocorr=True, flagbackup=False)
        flagdata(vis=name+'.ms',mode='manual', intent='*POINTING*,*SIDEBAND_RATIO*,*ATMOSPHERE*', flagbackup=False)
        flagdata(vis=name+'.ms',mode='shadow',flagbackup=False)
        flagmanager(vis=name+'.ms', mode='save', versionname='Apriori')

if (dofixsyscaltimes):
    from casarecipes.almahelpers import fixsyscaltimes
    for name in basename:
        fixsyscaltimes(name+'.ms')
      
if (docalibrate):
    for name in basename:
        print("Calibrating dataset "+name+" ...")
        tsys_caltable = name+'.ms.tsys'
        wvr_caltable = name+'.ms.wvr'
        if (dogencal):
            # Calibrate system temperature & water vapor radiometer
            # Generate Tsys calibration table
            if (not(os.path.isdir(tsys_caltable)) or clobberTsysTable):
                if verbose:
                    print("Generating Tsys table...")
                gencal(vis = name+'.ms',caltable = tsys_caltable, caltype = 'tsys')

            if verbose:
                print("Generated tsys table:")
                print(tsys_caltable)
            
            # Generate WVR calibration table
            if os.path.isdir(wvr_caltable) and not clobberWVRTable:
                print(f"Not generating the WVR table because it already exists and clobberWVRTable is set to False!")
            else:
                import shutil            
                if os.path.isdir(wvr_caltable) and clobberWVRTable:
                    shutil.rmtree(wvr_caltable)
                if verbose:
                    print("Generating WVR table...")
                mylogfile = casalog.logfile()
                casalog.setlogfile(name+'.ms.wvrgcal')
                wvrgcal(vis = name+'.ms', caltable = wvr_caltable, toffset = 0)
                casalog.setlogfile(mylogfile)

        if (doapplycal):
            if verbose:
                print("Creating Tsys map for applying the cals...")
            from casarecipes.almahelpers import tsysspwmap
            tsysmap = tsysspwmap(
                vis=name+'.ms',
                tsystable=tsys_caltable
            )[:spwmax+1] # Remove extraneous SPWs from tsysmap list

            if verbose:
                print("Applying Tsys and WVR calibration to fields that use their own Tsys...")
            for field in tsysfields_self:
                try:
                    applycal(
                        vis=name+".ms",
                        spw=spw0[name],
                        field=field,
                        gainfield=[field,field],
                        interp='linear',
                        gaintable=[name+'.ms.tsys',name+'.ms.wvr'],
                        spwmap=[tsysmap,[]],
                        flagbackup=True,
                        calwt=True
                    )
                except RuntimeError as exc:
                    exc = str(exc)
                    correct_msg = "Error in data selection specification: Field Expression: No match found for name"
                    if correct_msg in exc:
                        continue
                    else:
                        raise RuntimeError(f"{field} missing in {name}.ms") from exc

            if verbose:
                print("Applying Tsys and WVR calibration to fields that use another field's Tsys...")
            for field in tsysfields_alt:
                print("For field "+field+" using gainfield "+tsysfields_ref[field])
                applycal(
                    vis=name+".ms",
                    spw=spw0[name],
                    field=field,
                    gainfield=[tsysfields_ref[field],field],
                    interp='linear',
                    gaintable=[name+'.ms.tsys',name+'.ms.wvr'],
                    spwmap=[tsysmap,[]],
                    flagbackup=True,
                    calwt=True
                )

msname = date+'_'+band+'_all.ms'
if (doconcat):
    if (not(os.path.isdir(msname))):
        if verbose:
            print("Concating the msfiles...")
        concat(vis = [name + '.ms' for name in basename], concatvis = msname)
    else:
        print(f"Not concatting because {msname} already exists!")

outputvis = date+'_'+band+'.ms'   
if (dosplit):
    if (not(os.path.isdir(outputvis))):
        if verbose:
            print("Splitting the concatted msfiles...")
        split(
            vis=msname,
            outputvis=outputvis,
            datacolumn='corrected',
            spw=sciencespw,
            keepflags=False
        )
    else:
        print(f"Not splitting because {outputvis} already exists!")

msname = outputvis
if dosplit and verbose:
    print(f"New msfile is {msname}")
