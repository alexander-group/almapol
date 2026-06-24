####################### SELF CAL. CYCLE ########################################
import numpy as np

def mkimage(msname,imgname,mask=None, datacolumn='corrected',savemodel='modelcolumn'):
    tclean(msname,
           imagename = imgname,
           cell = str(mycell)+'arcsec',
           imsize = [512,512],
           deconvolver = 'clarkstokes',
           stokes = 'IQUV',
           interactive = True,
           weighting = 'briggs',
           robust = 0,
           datacolumn=datacolumn,
           niter = 1000,
           pbcor = True,
           parallel = True,
           mask=mask,
           savemodel=savemodel)

# FILL THESE VALUES IN HERE!!!
main_vis = 'PATH-TO-CALIBRATED-MS-FILE'
target  = "TARGET"
refant = 'REFANT'
img_root = target+"-img"
vis_root = 'vis-selfcal'
split_from_main = False

# Split off main calibrated ms file to apply selfcal
if (split_from_main):
    r = 0 
    mstransform(vis=main_vis, field=target, spw='', datacolumn='data', outputvis=f'{vis_root}-p{r}.ms')

# Calculate cellsize
tb.open(main_vis)
B_max = np.max(np.sqrt(tb.getcol('UVW')[0]**2 + tb.getcol('UVW')[1]**2 + tb.getcol('UVW')[2]**2))
tb.close()
tb.open(main_vis + '/SPECTRAL_WINDOW/')
nu_max = np.mean(tb.getcol('REF_FREQUENCY'))
tb.close()
mycell = ((3.e8 / nu_max) / B_max) * (180. / np.pi) * 3600. / 8.

# Calculate Number of antenna
tb.open(f'{main_vis}/ANTENNA')
Nant = tb.nrows()
tb.close()

# Calculate Integration time on source
msmd.open(f'{main_vis}')
field = msmd.fieldsforintent('OBSERVE_TARGET#ON_SOURCE')
t_int = msmd.timesforfield(field[0])
total_time = t_int[-1] - t_int[0]

def compute_min_sol_int(t_int = total_time, Nant = Nant):
    calstat_img = imstat(imagename=f'{img_root}-p0.image', stokes='I')
    peak = calstat_img['max'][0]
    calstat_res = imstat(imagename=f'{img_root}-p0.residual', stokes='I', box='50,50,100,100')
    rms = calstat_res['rms'][0]
    print(peak,rms)
    return total_time * (3*rms*np.sqrt(Nant-3)/peak)**2
    

def selfcal(msname,r=0):
    print(f"Running tclean on {msname} \n")
    if r ==0:
        mkimage(msname,f'{img_root}-p{r}',mask=None)
    else:
        mkimage(msname,f'{img_root}-p{r}',mask=f'{img_root}-p{r-1}.mask')
        
    while True:
        r+=1
        print(f"NOTE: Solution interval must satisfy t_sol > {compute_min_sol_int()}")
        solint = input(f"Enter solution interval (ex. 30s,4min...): ")
        print()
        calmode = input(f"Enter calmode type ('p' for phase only, 'ap' for amp+phase): ")
        print()
        if calmode == 'p':
            solnorm = False
        elif calmode == 'ap':
            solnorm = True
        else:
            raise Exception("Invalid input, please enter 'p' or 'ap'")
                    
        print(f"Running gaincal on {msname} \n")
        gaincal(vis=msname,caltable = f'{target}.scal.{r}{calmode}/',solint = str(solint),refantmode = 'strict',
                refant = refant,minsnr=3, combine='scan', gaintype='T',calmode=calmode,solnorm=solnorm)

        plotms(f'{target}.scal.{r}{calmode}',xaxis='time',yaxis='phase',gridrows=3,gridcols=3,iteraxis='antenna',coloraxis='spw', plotrange=[0,0,-180,180])
        user_input = input("Enter 'good' to applycal+split and continue, 'bad' to rerun gaincal, or 'done' to stop: ").strip().lower()

        if user_input == "good":
            print(f"Running applycal on {msname} \n")
            applycal(vis=msname, field='', gaintable=f'{target}.scal.{r}{calmode}/', gainfield='', applymode='calflag', interp=['linear'], calwt=False, parang=False)
            new_msname = f'{vis_root}-p{r}.ms'
            print(f"Splitting of corrected data from {msname} to {new_msname} \n")
            mstransform(vis=msname, field='', spw='', datacolumn='corrected', outputvis=new_msname)
            selfcal(new_msname,r=r)
            break   
        
        elif user_input == "bad":
            print("Rerunning Gaincal for different solution interval")
            r-=1
            continue
            
            
        elif user_input == "done":
            print(f"Running applycal on {msname} \n")
            applycal(vis=msname, field='', gaintable=f'{target}.scal.{r}{calmode}/', gainfield='', applymode='calflag', interp=['linear'], calwt=False, parang=False)
            new_msname = f'{vis_root}-p{r}.ms'
            print(f"Splitting of corrected data from {msname} to {new_msname} \n")
            mstransform(vis=msname, field='', spw='', datacolumn='corrected', outputvis=new_msname)
            print("Finished selfcal")
            break

        else:
            raise Exception("Invalid input, please enter 'good', 'bad', or 'done'.")
