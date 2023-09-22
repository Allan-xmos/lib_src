from asrc_utils import asrc_util
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

################################################################################################################
# OVERVIEW
#
# This script generates a set of test files for the supported input and output rates.
# It passes these through the golden reference "C" models and xsim, and
# Plots the FFTs, extracts the SNR, THD, and extracts MIPS estimate.
# All this info is annotated on the Plot which is saved to the otput folder.
#
# Note that both the C model is a dual-channel iplementations, so we pass them a pair of source files
# and since this is ASRC, we vary the frequency deviation parameter fDev.
# But, OS3 and DS3 are single channel apps - which is dealt with!
#
################################################################################################################


# Setup some basics
pkg_dir = Path(__file__).parent
xsim = False
fftPoints=1024 # note when updating the test tones with "updateSig" this is overwritten
FERR = 1.0  #this is an additional sample rate deviation applied to the inpt signal to test effect of errors

U = asrc_util(pkg_dir, True, fftPoints,[200], [500]) # create the util object
U.addRSTHeader("Performance information", 1) # start the RST it generates with a title
U.addRSTHeader("Chart data", 2) # start the RST it generates with a title

for fDev in [0.9999, 1.0, 1.0001]:  # for a set of different frequency deviations
    U.addRSTHeader("Frequency error: {:.6f}Hz".format(fDev), 3) #add a title to the RST for the freq deviation

    for opRate in U.allRates: # for each of the possible output sample rates
        U.addRSTHeader("Output Fs : {:,d}Hz".format(U.sampleRates[opRate]), 4) # add a subtitle to RST for the opRate

        # Choose the o/p rate and freq deviation
        U.setOpRate(opRate, fDev)

        no_results = True # the RST contains headings for all fDev, opRate and ipRate - so if this is an unsupported combination, add a warning to thr RST.
        for ipRate in U.allRates:# for each of the possible input sample rates
            # opportunity to choose different test freq, which also sets a safer fft size
            U.updateSig(ipRate, [int(fftPoints/5)], [int(fftPoints/4),int(fftPoints/6)], True) # specified in temrs of FFT o/p bin, when flag set true it auto-fills a logrithmic range for ch1 and 5% in for ch0

            # Make a set of input files based on range of sample rates supported
            ipFiles, sig = U.makeInputFiles([ipRate], FERR)   # makes the signals, saves data as files and returns some info about them

            # Put the input data through the golden "C" emulators
            opFiles, simLog = U.run_c_model(ipFiles, opRate, 4, fDev)

            # Itterate over all the input data files and channels
            for channels in ipFiles: # For each input sata set there will be an output one for each channel
                for channel in channels[0:2]:
                    print(channel)

                    if len(simLog[channel]) > 0: #at least one simulation ran for this combination of iprate, oprate and fdev
                        no_results = False
                        for sim in simLog[channel]:
                            opData = U.loadDataFromOutputFile(simLog[channel][sim])

                            # fft
                            opfft = U.rawFFT(opData['samples'])
                            oplabel = opData['labels']

                            # Get MHz utilization info from the log
                            info = U.scrapeCLog(opData)

                            # Calculate the SNR for each fft
                            opSNR = U.calcSNR(opfft, opData['chan'])

                            # Calculate the THD for each fft
                            opTHD = U.calcTHD(opfft, opData['chan'])

                            # Keep the results to plot later
                            text="SNR:{:.1f}dB\nTHD:{}dB\n".format(opSNR, opTHD)
                            U.pushPlotInfo(opfft, oplabel, text)

                            # Update log with these results
                            U.logResults(sim, ipRate, opRate, fDev, opData['chan'], opSNR, opTHD, info['total_mips'], info['ch0_mips'], info['ch1_mips'], info['log'])


                        #Plot the results
                        plotFile = U.plotFFT(U.plot_data, combine=False, title=U.makePlotTitle(simLog, channel), subtitles=U.plot_label, log=True, text=U.plot_text) # plots a grid of charts, one per cimulation model
                        U.makeRST(plotFile, ipRate, opRate, fDev, simLog[channel].keys()) # add this plot to a list to save as an RST file later
                        U.resetPlotInfo() # otherwise the next itteration of rates etc will add more plots to this instead of starting a new plot.
        if no_results:
            U.addRSTText("No SRC available for this scenario.")

U.log2csv() # Save the log file
U.addRSTHeader("Tabulated data", 2) # start the RST it generates with a title
U.addLog2RST() # adds the log, which is the tabulated results, to the RST file
U.saveRST("allPlots.rst") # Save the log file to the output folder

print("Done")
quit()

'''
                # if xsim
                if xsim:
                    # Put the input data through the XSIM test program
                    xFiles= U.run_xsim(ipFiles, opRate, fDev)
                    xdata = U.loadDataFromFiles(xFiles) # and load the result

                    # xsim model fft data
                    xfft = U.doFFT(xdata[r], ch)
                    xlabel = xdata[r]['labels'][ch]

                    # Get MHz utilization info from the log
                    util = U.scrapeXsimLog(xdata[r])

                    # Check the c-model results against the xsim results
                    matches = np.array_equal(xdata[r]['samples'], opdata[r]['samples'])
                    isClose = np.allclose(xdata[r]['samples'], opdata[r]['samples'], rtol=0.5**16, atol=0.5**28)
                    match = "Pass" if matches else "Close" if isClose else "Fail"

                    # Calculate the SNR for each fft
                    xSNR = U.calcSNR(xfft, xdata[r]['rate'], ch)

                    # Plot the result, and save the chart - just the "C" results here
                    text=["C SNR:{:.1f}dB\nMIPS:{:.1f}".format(opSNR, ch0mips + ch1mips),
                          "XSIM SNR:{:.1f}dB\nMIPS:2Ch CPU:{:.1f}\nPass/Fail:{}".format(xSNR, util, match)]
                    title = "Channel={}, IP={}, OP={}, FDEV={}, XSIM".format(ch,ipdata[r]['rate'], opRate, fDev)
                    U.plotFFT([opfft, xfft], combine=False, title=title, subtitles=["FIX ME", xlabel], log=True, text=text)

                    # Update log with these results
                    U.logResults("XSIM", ipdata[r]['rate'], opRate, fDev, ch, xSNR, util, txt=match)

'''

# TODO

# XSIM only ever supported for the ASRC XC implementation - do we need to support the others? There may be no existing test app...
# check log scraping for xsim, and is this OK on the chart, and in the log file
# add back the "pass/fail" test for xsim vs c
# the skip_xsim is just hard coded in the init, need to think about applynig to a subset?

# tidy up call to fft to make windowing a default off option
# go through the functions to use self.opRate, self.fDev everywhere
# legacy "list-factors" code can be removed
