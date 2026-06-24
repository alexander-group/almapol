# Script to calibrate ALMA polarimetry observations
# The script is run in two steps, depending on whether or not a polscan has been defined. 
# If polscan = None, the calibration will run until plotms displays the polarization ratio vs scan number (Fig 10 from tutorial)
# From this the user will need define the best scan to use for the cross-hand delay step in config.py, then rerun this script
# Note that the script does not check whether any step has actually executed correctly! 

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
    warnings.warn(f"No util file found at {utilfile}, please check that you have imported it!")

print("Now running calibrate.py")
print("Checking all needed variables are defined")

config_vars = [
"Lcal",
"Fcal",
"Bcal",
"Gcal",
"Trgt",
"refant",
"polscan",
"band",
"date",
"target_chan_avg",
"ms_to_calibrate",
"ms_to_split_target",
"ms_to_split_Gcal",
"ms_to_split_Lcal"
]
for v in config_vars:
    check_var(v)

msname = ms_to_calibrate
    
print("Will attempt to calibrate {:s} using:".format(ms_to_calibrate))
print("Field {:>12s} as Leakage  Calibrator".format(Lcal))
print("Field {:>12s} as Flux     Calibrator".format(Fcal))
print("Field {:>12s} as Bandpass Calibrator".format(Bcal))
print("Field {:>12s} as Gain     Calibrator".format(Gcal))
print("Field {:>12s} as Target".format(Trgt))

# Run this to do initial calibration up until cross-hand delays step
print("Starting parallel-hand calibration...")






if (polscan == None):
    print("No polscan specified. Script will stop after the polfromgain step.")
    if (docal_SetJy):
        date_obj = datetime.strptime(date, "%b-%d-%Y")   # parse
        date_for_setJy = date_obj.strftime("%d-%b-%Y")
        spix_q, spix_F, slope = get_recent_fcal_flux(date_for_setJy, band, Fcal)
        setjy(vis=ms_to_calibrate,field=Fcal,standard='manual',scalebychan=True,fluxdensity=[spix_F,0,0,0], spix=[slope,0], reffreq=str(spix_q)+'Hz')
    
    if (docal_Bandpass):
        print("Flagging Edge Channels...")
        flagdata(vis=msname, spw='*:0~3,*:60~63')
        print("Deriving bandpass...")
        #Gaincal and Bandpass solutions for bandpass calibrator
        gaincal(vis = msname, caltable = msname+'.G0ph', field = Bcal, gaintype = 'G', solint = 'int', calmode = 'p', spw = '*:20~45', refantmode = 'strict', refant = refant, smodel = [1,0,0,0])
        print("Written table {:s}".format(msname+'.G0ph'))
        bandpass(vis = msname, caltable = msname+'.Bscan', field = Bcal, solint = 'inf', combine = 'scan,obs', refant = refant, solnorm = True, gaintable = [msname+'.G0ph'], interp = ['nearest'])
        print("Written table {:s}".format(msname+'.Bscan'))

    if (docal_Gain):
        print("Solving for complex gain phase(t)...")
        # Gain calibration for bandpass, flux, and phase calibrators - phase only then on-the-fly amp
        gaincal(vis = msname, caltable = msname+'.G2ph', gaintype = 'G', field = Bcal+','+Fcal+','+Gcal, solint = 'int', refant = refant, refantmode = 'strict', calmode = 'p', gaintable = [msname+'.Bscan'], interp = ['nearest'])
        print("Written table {:s}".format(msname+'.G2ph'))
        print("Solving for complex gain amplitude(t)...")
        gaincal(vis = msname, caltable = msname+'.G2amp', field = Bcal+','+Fcal+','+Gcal, solint = 'int', refant = refant, refantmode = 'strict', gaintype = 'T', calmode = 'a', gaintable = [msname+'.Bscan',msname+'.G2ph'], interp = ['nearest','nearest'])
        print("Written table {:s}".format(msname+'.G2amp'))

        plotms(vis=msname+'.Bscan', xaxis='frequency', yaxis='amp',coloraxis='antenna1', iteraxis='spw', gridrows=2, gridcols=2, showgui=False, plotfile="fig7.png")
        
    if (docal_Fluxscale):
        print("Running fluxscale...")

        # Apply absolute flux for bandpass, flux, and phase calibrators
        fluxscale(vis = msname, caltable = msname+'.G2amp', fluxtable = msname+'.flux', reference = Fcal, transfer = Bcal+','+Gcal)

        print("Written table {:s}".format(msname+'.flux'))

    if (applycal_ParallelHand):
        print("Applying parallel hand calibrations to data...")
        # Apply solutions for bandpass, flux, and phase calibrators
        applycal(vis = msname, field = Bcal+','+Fcal+','+Gcal, calwt = True, gaintable = [msname+'.Bscan',msname+'.G2ph',msname+'.flux'], interp = ['nearest','linear','linear'], parang = False)
        print("... parallel hand calibrations applied!")

        plotms(vis=msname+'', field=Bcal, spw='0', xaxis='parang', yaxis='amp', correlation='XX,YY',ydatacolumn='corrected', avgchannel='64', avgbaseline=True, coloraxis='corr', iteraxis='field', showgui=False, plotfile="fig8.png")
        plotms(vis=msname+'', field=Gcal, spw='0', xaxis='parang', yaxis='amp', correlation='XX,YY',ydatacolumn='corrected', avgchannel='64', avgbaseline=True, coloraxis='corr', showgui=False, plotfile="fig9.png")
        
    ############################
    # POLARIZATION CALIBRATION #
    ############################
    print("Starting polarization calibration...")
    if (dopol_Gain):
        print("Solving for (preliminary) gains on leakage calibrator...")
        # Solve for Gains on polarization calibrator        
        gaincal(vis = msname, caltable = msname+'.G1', field = Lcal, solint = 'int', refant = refant, refantmode = 'strict', smodel = [1,0,0,0], gaintable = msname+'.Bscan', interp = 'nearest')  
        print("Written table {:s}".format(msname+'.G1'))     
        print("Note: these gain solutions will have absorbed the polarization of the calibrator!") 
        
    if (dopol_ApplyGainBP):
        print("Applying bandpass and (preliminary) gain calibration to leakage calibrator...")
       # Apply Bandpass and Gain solutions to polarization calibrator    
        applycal(vis = msname, field = Lcal, calwt = False, gaintable = [msname+'.Bscan',msname+'.G1'], interp = ['nearest','linear'], parang=False)     

        plotms(vis=msname+'', field=Lcal, avgchannel='64', xaxis='parangle', yaxis='amp', ydatacolumn='corrected', correlation='XX,YY', coloraxis='corr', showgui=False, plotfile="fig11.png")
        
    if (dopol_QU):
        print("Deriving polarization of leakage calibrator...")
        # Extract linear polarization of leakage calibrator        
        qu=polfromgain(vis=msname, tablein=msname+'.G1', caltable=msname+'.G1a')
        print("Written table {:s}".format(msname+'.G1a'))     
        print("Extracted linear polarization of leakage calibrator (field {:s}):".format(Lcal))
        print(qu)
        # PLOTMS to determine best pol scan
        # For the cross-hand delay calculation we need to choose a scan where the source's cross-hand contribution is maximum (in absolute value) 
        # to minimize the mean effect of instrumental polarization. This scan would be the one where the gain ratio is near the mean value.
        # See fig 10 of the tutorial https://casaguides.nrao.edu/index.php/3C286_Band6Pol_Calibration_for_CASA_6.6.1#Cross-hand_delay

        plotms(vis=msname+'.G1', xaxis='scan', yaxis='GainAmp', coloraxis='antenna1', correlation='/', showgui=False, plotfile="fig10.png")
        
        print("Ending polarization script here. Set polscan in config.py and rerun.")

if (polscan!=None):
    print("Polscan has been specified as {}".format(polscan))
    print("This script will now re-start at the cross-hand delay step.")
    
    if (dopol_CrossHandDelay):
        print("Deriving cross-hand delays...")
        # Solve for Cross-hand delay on polarization calibrator
        plotms(vis = msname+'',ydatacolumn = 'corrected',xaxis = 'freq',yaxis = 'phase',field = '0',avgtime = '1e9',correlation = 'XY,YX',spw = '',antenna = refant,iteraxis = 'baseline',coloraxis = 'corr',plotrange = [0,0,-180,180], showgui=True, plotfile="fig12.png")
        
        gaincal(vis = msname, caltable = msname+'.Kcrs', scan = polscan, gaintype = 'KCROSS', solint = 'inf', refant = refant, refantmode = 'strict', smodel = [1,0,1,0], gaintable = [msname+'.Bscan',msname+'.G1'], interp = ['nearest','linear'])  
        print("Written table {:s}".format(msname+'.Kcrs'))     

    if (dopol_ApplyKcrs):
        print("Applying cross-hand-delays to leakage calibrator...")
        # Apply cross-hand delay (and Gains + BP) on polarization calibrator      
        applycal(vis = msname, field = Lcal, calwt = False, gaintable = [msname+'.Bscan',msname+'.G1',msname+'.Kcrs'], interp = ['nearest','linear','nearest'])
        print("Cross-hand delays applied (to leakage calibrator only)")

        plotms(vis = msname+'',ydatacolumn = 'corrected',xaxis = 'freq',yaxis = 'phase',field = '0',avgtime = '1e9',correlation = 'XY,YX',spw = '',antenna = refant,iteraxis = 'baseline',coloraxis = 'corr',plotrange = [0,0,-180,180], showgui=False, plotfile="fig13.png")
        
    # Estimate XY-phase offset and source polarization from the cross-hands on polarization calibrator
    if (dopol_XYphase):
        # Fig 14 (run again later for Fig 17)
        plotms(vis = msname+'',ydatacolumn = 'corrected',xdatacolumn = 'corrected',xaxis = 'real',yaxis = 'imag',field = '0',avgtime = '1e9',avgchannel='64',avgbaseline = True,correlation = 'XY,YX',spw = '3',coloraxis = 'corr',plotrange = [-0.06,0.06,-0.06,0.06], showgui=False, plotfile="fig14.png")

        print("Deriving instrumental XY-phase offset (running polcal)...")
        S = polcal(vis = msname, caltable = msname+'.Xfparang', field = Lcal, poltype = 'Xfparang+QU', solint = 'inf', combine = 'scan,obs', preavg = 300, smodel = qu[Lcal]['SpwAve'], gaintable = [msname+'.Bscan',msname+'.G1',msname+'.Kcrs'], interp = ['nearest','linear','nearest'])
        print("Written table {:s}".format(msname+'.Xfparang'))

        # Fig 15
        plotms(vis=msname+'.Xfparang', xaxis='frequency', yaxis='phase', iteraxis='antenna', coloraxis='spw', showgui=True, plotfile="fig15.png")
        
        
    if (dopol_ApplyXYphase):
        print("Applying XY-phase calibration to leakage calibrator...")
        # Apply XY-phase+QU (and Cross-hand delays + Gains + BP)) from the cross-hands on polarization calibrator   
        applycal(vis = msname, field = Lcal, calwt = [True,True,False,False], gaintable = [msname+'.Bscan',msname+'.G1',msname+'.Kcrs',msname+'.Xfparang'], interp = ['nearest','linear','nearest','nearest'])
        print("XY-phase calibration applied (to leakage calibrator only)")

        # Fig 16
        plotms(vis = msname+'',ydatacolumn = 'corrected',xaxis = 'freq',yaxis = 'phase',field = '0',avgtime = '1e9',avgscan = True,correlation = 'XY,YX',spw = '',coloraxis = 'corr',iteraxis = 'baseline',plotrange=[0,0,-180,180], showgui=True, plotfile="fig16.png")

        # Fig 17
        plotms(vis = msname+'',ydatacolumn = 'corrected',xdatacolumn = 'corrected',xaxis = 'real',yaxis = 'imag',field = '0',avgtime = '1e9',avgchannel='64',avgbaseline = True,correlation = 'XY,YX',spw = '3',coloraxis = 'corr',plotrange = [-0.06,0.06,-0.06,0.06], showgui=False, plotfile="fig17.png")

        
    if (dopol_RegenLcalGains):
        print("Recalculating gains on leakage calibrator...")
        # Revise gain with good source pol estimate
        gaincal(vis = msname, caltable = msname+'.G2.polcal', field = Lcal, solint = 'int', refant = refant, refantmode = 'strict', smodel = S[Lcal]['SpwAve'], gaintable = [msname+'.Bscan'], interp = ['nearest'], parang = True) 
        print("Written table {:s}".format(msname+'.G2.polcal'))

        # Fig 18
        plotms(vis=msname+'.G1', xaxis='time', yaxis='amp', field=Lcal, correlation='/', coloraxis='antenna1', showgui=False,
               plotfile="fig18a.png")
        plotms(vis=msname+'.G2.polcal', xaxis='time', yaxis='amp', field=Lcal, correlation='/', coloraxis='antenna1', showgui=False, plotfile="fig18b.png")


        # Check that QU are near zero
        print("Deriving QU from new gain table (these should be zero)...")
        qu2 = polfromgain(vis=msname, tablein=msname+'.G2.polcal', caltable=msname+'.G2a.polcal')
        print("Extracted linear polarization of leakage calibrator (field {:s}) from new gain table:".format(Lcal))
        print(qu2)
        
    if (dopol_Leakage):
        print("Deriving leakage solution = antenna D terms (running polcal)...")
        # Solve for the Leakage Terms on polarization calibrator   
        polcal(vis = msname, caltable = msname+'.Df0gen', field = Lcal, solint = 'inf', combine = 'obs,scan', preavg = 300, poltype = 'Dflls', refant = '', smodel = S[Lcal]['SpwAve'], gaintable = [msname+'.Bscan',msname+'.G2.polcal',msname+'.Kcrs',msname+'.Xfparang'], gainfield = ['','','',''], interp = ['nearest','linear','nearest','nearest']) 
        print("Written table {:s}".format(msname+'.Df0gen'))             

        # Fig 19 (the tutorial only has screenshots for the first command in each pair)
        plotms(vis=msname+'.Df0gen', xaxis='frequency', yaxis='amp', spw='0,1', iteraxis='antenna', coloraxis='corr', gridrows=3, gridcols=2, showgui=False, plotfile="fig19a.png")
        plotms(vis=msname+'.Df0gen', xaxis='frequency', yaxis='amp', spw='2,3', iteraxis='antenna', coloraxis='corr', gridrows=3, gridcols=2, showgui=False, plotfile="fig19b.png")

        # Fig 20
        plotms(vis=msname+'.Df0gen', xaxis='frequency', yaxis='real', spw='0,1', iteraxis='antenna', coloraxis='corr', gridrows=3, gridcols=2, showgui=False, plotfile="fig20a.png")
        plotms(vis=msname+'.Df0gen', xaxis='frequency', yaxis='real', spw='2,3', iteraxis='antenna', coloraxis='corr', gridrows=3, gridcols=2, showgui=False, plotfile="fig20b.png")

        # Fig 21
        plotms(vis=msname+'.Df0gen', xaxis='frequency', yaxis='imag', spw='0,1', iteraxis='antenna', coloraxis='corr', gridrows=3, gridcols=2, showgui=False, plotfile="fig21a.png")
        plotms(vis=msname+'.Df0gen', xaxis='frequency', yaxis='imag', spw='2,3', iteraxis='antenna', coloraxis='corr', gridrows=3, gridcols=2, showgui=False, plotfile="fig21b.png")

        
    if (dopol_XYamp):
        print("Deriving X/Y amplitude ratio...")
        # Solving the Global Normalized Gain Amplitudes on polarization calibrator
        gaincal(vis = msname, caltable = msname+'.Gxyamp', field = Lcal, solint = 'inf', combine = 'obs,scan', refant = refant, refantmode = 'strict', gaintype = 'G', calmode = 'a', smodel = S[Lcal]['SpwAve'], gaintable = [msname+'.Bscan',msname+'.G2.polcal',msname+'.Kcrs',msname+'.Xfparang',msname+'.Df0gen'], gainfield = ['','','','',''], interp = ['nearest','linear','nearest','nearest','nearest'], solnorm = True, parang = True) 
        print("Written table {:s}".format(msname+'.Gxyamp'))     

        # Fig 22: XY and YX
        plotms(vis=msname+'.Gxyamp', xaxis='antenna1', yaxis='amp', coloraxis='corr', iteraxis='spw', gridrows=2, gridcols=2, showgui=False, plotfile="fig22.png")
        # Fig 23: pol ratio
        plotms(vis=msname+'.Gxyamp', xaxis='antenna1', yaxis='amp', correlation='/', coloraxis='antenna1', iteraxis='spw', gridrows=2, gridcols=2, showgui=False, plotfile="fig23.png")
        
    if (applycal_Lcal):
        print("Applying bandpass, gain, cross-hand delay, XYphase, and leakage calibration to leakage calibrator...")
        # Apply all solutions to leakage calibrator   
        applycal(vis = msname, field = Lcal, calwt = [True,True,False,False,False], gaintable = [msname+'.Bscan',msname+'.G2.polcal',msname+'.Kcrs',msname+'.Xfparang',msname+'.Df0gen'], interp = ['nearest','linear','linear','nearest','nearest'], gainfield = ['','','','',''], parang = True) 
        print("Leakage calibrator data now calibrated to unity amplitude")

        # Fig 26
        plotms(vis = msname+'',ydatacolumn = 'corrected',xdatacolumn = 'corrected',xaxis = 'real',yaxis = 'imag',field = '0',avgtime = '1e9',avgchannel='64',avgbaseline = True,correlation = 'XY,YX',spw = '3',coloraxis = 'corr',plotrange = [-0.06,0.06,-0.06,0.06], showgui=False, plotfile="fig26.png")
        # Fig 27
        plotms(vis = msname+'',xaxis = 'chan',yaxis = 'amp',ydatacolumn = 'corrected',field = '0',avgtime = '1e9',avgscan = True,coloraxis = 'corr', showgui=False, plotfile="fig27.png")
        # Fig 28
        plotms(vis = msname+'',xaxis = 'chan',yaxis = 'phase',ydatacolumn = 'corrected',field = '0',avgtime = '1e9',avgscan = True,coloraxis = 'corr', showgui=False, plotfile="fig28.png")
        # Fig 29
        plotms(vis = msname+'',xaxis = 'freq',yaxis = 'phase',ydatacolumn = 'corrected',field = '0',avgtime = '1e9',avgscan = True,correlation = 'XY,YX',coloraxis = 'corr',iteraxis = 'baseline', showgui=False, plotfile="fig29.png")

        
    if (applycal_Trgt):
        print("Applying bandpass, gain, flux, cross-hand delay, XYphase, leakage, and X/Y amp calibration to gaincal (field {:s}) and target (field {:s})...".format(Gcal, Trgt))
        # Apply solutions to target
        # Fig 30 and 31 (run before and after target calibration to see the difference)
        plotms(vis = msname+'',field = Trgt,xaxis = 'real',yaxis = 'imag',spw = '0',ydatacolumn = 'data',xdatacolumn = 'data',avgchannel = '64',avgtime = '1e9',avgscan = True,coloraxis = 'corr', showgui=False, plotfile="fig30.png")

        applycal(vis = msname, field = Gcal+','+Trgt, calwt = [True,True,False,False,False,False,False], gaintable = [msname+'.Bscan',msname+'.G2ph',msname+'.flux',msname+'.Kcrs',msname+'.Xfparang',msname+'.Df0gen',msname+'.Gxyamp'], interp = ['nearest','linear','linear','nearest','nearest','nearest','nearest'], gainfield = ['',Gcal,Gcal,'','','',''], parang = True)

        # Fig 30 and 31 (run before and after target calibration to see the difference)
        plotms(vis = msname+'',field = Trgt,xaxis = 'real',yaxis = 'imag',spw = '0',ydatacolumn = 'corrected',xdatacolumn = 'corrected',avgchannel = '64',avgtime = '1e9',avgscan = True,coloraxis = 'corr', showgui=False, plotfile="fig31.png")

        
    print("Calibration complete!")
    
    if (dosplit_Target):
        # split off target field and channel average if requested
        print("Splitting off target ms: ",ms_to_split_target)
        print("Using field: ",Trgt)
        print("Averaging {:d} channels".format(target_chan_avg))
        split(vis = msname,outputvis = ms_to_split_target,field = Trgt ,datacolumn = 'corrected',width = target_chan_avg)
        print("Target data have been written to {:s}".format(ms_to_split_target))
    if (dosplit_Gcal):
        # split off target field and channel average if requested
        print("Splitting off gain calibrator ms: ",ms_to_split_Gcal)
        print("Using field: ",Gcal)
        print("Averaging {:d} channels".format(target_chan_avg))
        split(vis = msname,outputvis = ms_to_split_Gcal,field = Gcal ,datacolumn = 'corrected',width = target_chan_avg)
        print("Gain calibrator data have been written to {:s}".format(ms_to_split_Gcal))
    if (dosplit_Lcal):
        # split off target field and channel average if requested
        print("Splitting off gain calibrator ms: ",ms_to_split_Lcal)
        print("Using field: ",Gcal)
        print("Averaging {:d} channels".format(target_chan_avg))
        split(vis = msname,outputvis = ms_to_split_Lcal,field = Lcal ,datacolumn = 'corrected',width = target_chan_avg)
        print("Gain calibrator data have been written to {:s}".format(ms_to_split_Lcal))
    
