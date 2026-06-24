# Plotms commands from the 3C286 polarization CASA guide
# https://casaguides.nrao.edu/index.php/3C286_Band6Pol_Calibration_for_CASA_6.6.1

# Fig 7
# Run after docal_SetJy, docal_Bandpass, and docal_Gain are all complete
#plotms(vis='3c286_Band6.ms.Bscan', xaxis='frequency', yaxis='amp',coloraxis='antenna1', iteraxis='spw', gridrows=2, gridcols=2)

# Fig 8 and 9 remember to page this display!
# Run after applycal_ParallelHand
#plotms(vis='3c286_Band6.ms', field='J1256-0547,J1310+3220', spw='0', xaxis='parang', yaxis='amp', correlation='XX,YY',ydatacolumn='corrected', avgchannel='128', avgbaseline=True, coloraxis='corr', iteraxis='field')

# Fig 10
# Run after dopol_Gain
#plotms(vis='3c286_Band6.ms.G1', xaxis='scan', yaxis='GainAmp', coloraxis='antenna1', correlation='/')

# Fig 11
# Run after dopol_ApplyGainBP
#plotms(vis='3c286_Band6.ms', field='0', avgchannel='64', xaxis='parangle', yaxis='amp', ydatacolumn='corrected', correlation='XX,YY', coloraxis='corr')

# Fig 12 and 13 (run twice, before and after applycal)
# Run before dopol_CrossHandDelay and then again after dopol_ApplyKcrs to check that it worked
#plotms(vis = '3c286_Band6.ms',ydatacolumn = 'corrected',xaxis = 'freq',yaxis = 'phase',field = '0',avgtime = '1e9',correlation = 'XY,YX',spw = '',antenna = 'DA48',iteraxis = 'baseline',coloraxis = 'corr',plotrange = [0,0,-180,180])

# Fig 14 (run again later for Fig 17)
# 
#plotms(vis = '3c286_Band6.ms',ydatacolumn = 'corrected',xdatacolumn = 'corrected',xaxis = 'real',yaxis = 'imag',field = '0',avgtime = '1e9',avgchannel = '128',avgbaseline = True,correlation = 'XY,YX',spw = '3',coloraxis = 'corr',plotrange = [-0.06,0.06,-0.06,0.06])

# Fig 15
#plotms(vis='3c286_Band6.ms.Xfparang', xaxis='frequency', yaxis='phase', iteraxis='antenna', coloraxis='spw')

# Fig 16
#plotms(vis = '3c286_Band6.ms',ydatacolumn = 'corrected',xaxis = 'freq',yaxis = 'phase',field = '0',avgtime = '1e9',avgscan = True,correlation = 'XY,YX',spw = '',coloraxis = 'corr',iteraxis = 'baseline',plotrange=[0,0,-180,180])#,antenna='DA41&DA48') # Tutorial figure looks only at DA41&DA48

# Fig 17
# See Fig 14 above

# Fig 18
#plotms(vis='3c286_Band6.ms.G1', xaxis='time', yaxis='amp', field='J1337-1257', correlation='/', coloraxis='antenna1')
#plotms(vis='3c286_Band6.ms.G2.polcal', xaxis='time', yaxis='amp', field='J1337-1257', correlation='/', coloraxis='antenna1')

# Fig 19 (the tutorial only has screenshots for the first command in each pair)
#plotms(vis='3c286_Band6.ms.Df0gen', xaxis='frequency', yaxis='amp', spw='0,1', iteraxis='antenna', coloraxis='corr', gridrows=3, gridcols=2)
#plotms(vis='3c286_Band6.ms.Df0gen', xaxis='frequency', yaxis='amp', spw='2,3', iteraxis='antenna', coloraxis='corr', gridrows=3, gridcols=2)

# Fig 20
#plotms(vis='3c286_Band6.ms.Df0gen', xaxis='frequency', yaxis='real', spw='0,1', iteraxis='antenna', coloraxis='corr', gridrows=3, gridcols=2)
#plotms(vis='3c286_Band6.ms.Df0gen', xaxis='frequency', yaxis='real', spw='2,3', iteraxis='antenna', coloraxis='corr', gridrows=3, gridcols=2)

# Fig 21
#plotms(vis='3c286_Band6.ms.Df0gen', xaxis='frequency', yaxis='imag', spw='0,1', iteraxis='antenna', coloraxis='corr', gridrows=3, gridcols=2)
#plotms(vis='3c286_Band6.ms.Df0gen', xaxis='frequency', yaxis='imag', spw='2,3', iteraxis='antenna', coloraxis='corr', gridrows=3, gridcols=2)

# Fig 22: XY and YX
#plotms(vis='3c286_Band6.ms.Gxyamp', xaxis='antenna1', yaxis='amp', coloraxis='corr', iteraxis='spw', gridrows=2, gridcols=2)
# Fig 23: pol ratio
#plotms(vis='3c286_Band6.ms.Gxyamp', xaxis='antenna1', yaxis='amp', correlation='/', coloraxis='antenna1', iteraxis='spw', gridrows=2, gridcols=2)

# Fig 26
#plotms(vis = '3c286_Band6.ms',ydatacolumn = 'corrected',xdatacolumn = 'corrected',xaxis = 'real',yaxis = 'imag',field = '0',avgtime = '1e9',avgchannel = '128',avgbaseline = True,correlation = 'XY,YX',spw = '3',coloraxis = 'corr',plotrange = [-0.06,0.06,-0.06,0.06])
# Fig 27
# plotms(vis = '3c286_Band6.ms',xaxis = 'chan',yaxis = 'amp',ydatacolumn = 'corrected',field = '0',avgtime = '1e9',avgscan = True,coloraxis = 'corr')
# Fig 28
#plotms(vis = '3c286_Band6.ms',xaxis = 'chan',yaxis = 'phase',ydatacolumn = 'corrected',field = '0',avgtime = '1e9',avgscan = True,coloraxis = 'corr')
# Fig 29
# plotms(vis = '3c286_Band6.ms',xaxis = 'freq',yaxis = 'phase',ydatacolumn = 'corrected',field = '0',avgtime = '1e9',avgscan = True,correlation = 'XY,YX',coloraxis = 'corr',iteraxis = 'baseline')

# Fig 30 and 31 (run before and after target calibration to see the difference)
plotms(vis = '3c286_Band6.ms',field = '4',xaxis = 'real',yaxis = 'imag',spw = '0',ydatacolumn = 'data',xdatacolumn = 'data',avgchannel = '64',avgtime = '1e9',avgscan = True,coloraxis = 'corr')
